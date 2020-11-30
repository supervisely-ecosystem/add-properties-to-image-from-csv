import os
import csv
import supervisely_lib as sly

my_app = sly.AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ["modal.state.slyProjectId"])

CSV_PATH_REMOTE = os.environ["modal.state.csvPath"]
IMAGE_TAG_NAME = os.environ["modal.state.tagName"]
CSV_COLUMN_NAME = os.environ["modal.state.columnName"]
ASSIGN_AS = os.environ["modal.state.assignAs"]
RESOLVE = os.environ["modal.state.resolve"]
RES_PROJECT_NAME = os.environ["modal.state.resultProjectName"]

PROJECT = None
RES_PROJECT = None

META: sly.ProjectMeta = None
RES_META: sly.ProjectMeta = None

CSV_INDEX = None
CSV_COLUMNS = None

api = sly.Api.from_env()


def read_csv_and_create_index():
    global CSV_INDEX, CSV_COLUMNS

    CSV_INDEX = {}

    csv_path_local = os.path.join(my_app.data_dir, sly.fs.get_file_name_with_ext(CSV_PATH_REMOTE))
    api.file.download(TEAM_ID, CSV_PATH_REMOTE, csv_path_local)

    with open(csv_path_local, "r") as f:
        reader = csv.DictReader(f)
        CSV_COLUMNS = reader.fieldnames
        if CSV_COLUMN_NAME not in CSV_COLUMNS:
            raise ValueError("Column {!r} not found in {!r}".format(CSV_COLUMN_NAME, CSV_PATH_REMOTE))
        for row in reader:
            filtered_row = row.copy()
            filtered_row.pop(CSV_COLUMN_NAME, None)
            CSV_INDEX[row[CSV_COLUMN_NAME].strip()] = filtered_row

    sly.fs.silent_remove(csv_path_local)


def read_and_validate_project_meta():
    global META, RES_META
    meta_json = api.project.get_meta(PROJECT_ID)
    META = sly.ProjectMeta.from_json(meta_json)
    tag_meta = META.get_tag_meta(IMAGE_TAG_NAME)
    if tag_meta is None:
        raise ValueError("Tag {!r} not found in project {!r}".format(IMAGE_TAG_NAME, project.name))
    RES_META = META.clone()


def add_tags_to_meta():
    global RES_META
    for column_name in CSV_COLUMNS:
        tag_meta: sly.TagMeta = RES_META.get_tag_meta(column_name)
        if tag_meta is None:
            RES_META = RES_META.add_tag_meta(sly.TagMeta(column_name, value_type=sly.TagValueType.ANY_STRING))
        else:
            if RESOLVE == "skip":
                continue
            elif RESOLVE == "replace" and tag_meta.value_type != sly.TagValueType.ANY_STRING:
                raise TypeError("Type of existing tag {!r} is not string".format(tag_meta.name))
            elif RESOLVE == "raise":
                raise RuntimeError("Tag {!r} already exists in project {!r}".format(tag_meta.name, PROJECT.name))


def assign_csv_row_as_metadata(image_id, image_name, input_meta, row):
    same_keys = input_meta.keys() & row.keys()
    if len(same_keys) > 0:
        if RESOLVE == "skip":
            my_app.logger.warn("Image {!r} (id={}): duplicate keys {} in metadata. Image is skipped"
                               .format(image_name, image_id, same_keys))
            return
        elif RESOLVE == "raise":
            raise KeyError("Image {!r} (id={}): duplicate keys {} in metadata."
                           .format(image_name, image_id, same_keys))
    return {**input_meta, **row}


def assign_csv_row_as_tags(image_id, image_name, res_ann, row):
    new_tags = []
    for k, v in row.items():
        tag_meta = RES_META.get_tag_meta(k)
        if tag_meta is None:
            raise RuntimeError("Tag {!r} not found in resulting project {!r}".format(k, RES_PROJECT.name))
        existing_tag = res_ann.img_tags.get(k)
        if existing_tag is None:
            new_tags.append(sly.Tag(tag_meta, value=v))
        else:
            if RESOLVE == "skip":
                continue
            elif RESOLVE == "raise":
                raise KeyError("Image {!r} (id={}): tag {!r} exists".format(image_name, image_id, k))
            elif RESOLVE == "replace":
                res_ann = res_ann.delete_tag_by_name(k)
                new_tags.append(sly.Tag(tag_meta, value=v))

    res_ann = res_ann.add_tags(new_tags)
    return res_ann


def main():
    global PROJECT, RES_PROJECT, RES_PROJECT_NAME

    PROJECT = api.project.get_info_by_id(PROJECT_ID)
    if RES_PROJECT_NAME == "":
        RES_PROJECT_NAME = PROJECT.name

    read_and_validate_project_meta()
    read_csv_and_create_index()

    RES_PROJECT = api.project.create(WORKSPACE_ID, RES_PROJECT_NAME, change_name_if_conflict=True)
    my_app.logger.info("Result Project is created (name={!r}; id={})".format(RES_PROJECT.name, RES_PROJECT.id))

    if ASSIGN_AS == "tags":
        add_tags_to_meta()

    api.project.update_meta(RES_PROJECT.id, RES_META.to_json())

    progress = sly.Progress("Processing", PROJECT.images_count, ext_logger=my_app.logger)
    for dataset in api.dataset.get_list(PROJECT.id):
        res_dataset = api.dataset.create(RES_PROJECT.id, dataset.name)
        ds_images = api.image.get_list(dataset.id)
        for batch in sly.batched(ds_images):
            image_ids = [image_info.id for image_info in batch]
            image_names = [image_info.name for image_info in batch]
            image_metas = [image_info.meta for image_info in batch]

            ann_infos = api.annotation.download_batch(dataset.id, image_ids)
            anns = [sly.Annotation.from_json(ann_info.annotation, META) for ann_info in ann_infos]

            original_ids = []
            res_image_names = []
            res_anns = []
            res_metas = []

            for image_id, image_name, image_meta, ann in zip(image_ids, image_names, image_metas, anns):
                tag: sly.Tag = ann.img_tags.get(IMAGE_TAG_NAME)
                if tag is None:
                    my_app.logger.warn("Image {!r} in dataset {!r} doesn't have tag {!r}. Image is skipped"
                                       .format(image_name, dataset.name, IMAGE_TAG_NAME))
                    progress.iter_done_report()
                    continue

                csv_row = CSV_INDEX.get(str(tag.value), None)
                if csv_row is None:
                    my_app.logger.warn("Match not found (id={}, name={!r}, dataset={!r}, tag_value={!r}). Image is skipped"
                                       .format(image_id, image_name, dataset.name, str(tag.value)))
                    progress.iter_done_report()
                    continue

                res_ann = ann.clone()
                res_meta = image_meta.copy()

                if ASSIGN_AS == "tags":
                    res_ann = assign_csv_row_as_tags(image_id, image_name, res_ann, csv_row)
                else:  # metadata
                    res_meta = assign_csv_row_as_metadata(image_id, image_name, image_meta, csv_row)

                original_ids.append(image_id)
                res_image_names.append(image_name)
                res_anns.append(res_ann)
                res_metas.append(res_meta)

            res_image_infos = api.image.upload_ids(res_dataset.id, res_image_names, original_ids, metas=res_metas)
            res_image_ids = [image_info.id for image_info in res_image_infos]
            api.annotation.upload_anns(res_image_ids, res_anns)
            progress.iters_done_report(len(res_image_ids))

    api.task.set_output_project(task_id, RES_PROJECT.id, RES_PROJECT.name)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
