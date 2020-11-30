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
RESULT_PROJECT_NAME = os.environ["modal.state.resultProjectName"]

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

    api.project.update_meta(RES_PROJECT.id, RES_META.to_json())


def assign_csv_row_as_metadata(image_id, image_name, input_meta, row):
    same_keys = dict_a.keys() & dict_b.keys()
    if len(same_keys) > 0:
        if RESOLVE == "skip":
            my_app.logger.warn("Image {!r} (id={}): duplicate keys {} in metadata. Image is skipped"
                               .format(image_name, image_id, same_keys))
            return
        elif RESOLVE == "raise":
            raise KeyError("Image {!r} (id={}): duplicate keys {} in metadata."
                           .format(image_name, image_id, same_keys))
    return {**input_meta, **row}


def main():
    global PROJECT, RES_PROJECT, RESULT_PROJECT_NAME

    PROJECT = api.project.get_info_by_id(PROJECT_ID)
    if RESULT_PROJECT_NAME == "":
        RESULT_PROJECT_NAME = PROJECT.name

    read_and_validate_project_meta()
    read_csv_and_create_index()

    RES_PROJECT = api.project.create(WORKSPACE_ID, RESULT_PROJECT_NAME, change_name_if_conflict=True)
    my_app.logger.info("Result Project is created (name={!r}; id={})".format(RES_PROJECT.name, RES_PROJECT.id))

    if ASSIGN_AS == "tags":
        add_tags_to_meta()
    else:
        api.project.update_meta(RES_PROJECT.id, RES_META.to_json())

    for dataset in api.dataset.get_list(PROJECT.id):
        res_dataset = api.dataset.create(RES_PROJECT.id, dataset.name)
        ds_images = api.image.get_list(dataset.id)
        for batch in sly.batched(ds_images):
            image_ids = [image_info.id for image_info in batch]
            image_names = [image_info.name for image_info in batch]
            image_metas = [image_info.meta for image_info in batch]

            ann_infos = api.annotation.download_batch(dataset.id, image_ids)
            anns = [sly.Annotation.from_json(ann_info.annotation, META) for ann_info in ann_infos]

            final_ids = []
            res_image_name = []
            res_anns = []
            res_metas = []

            for image_id, image_name, image_meta, ann in zip(image_ids, image_names, image_metas, anns):
                tag: sly.Tag = ann.img_tags.get(IMAGE_TAG_NAME)
                if tag is None:
                    my_app.logger.warn("Image {!r} in dataset {!r} doesn't have tag {!r}. Image is skipped"
                                       .format(image_name, dataset.name, IMAGE_TAG_NAME))
                    continue

                csv_row = CSV_INDEX.get(str(tag.value), None)
                if csv_row is None:
                    my_app.logger.warn("Match not found (id={}, name={!r}, dataset={!r}, tag_value={!r}). Image is skipped"
                                       .format(image_id, image_name, dataset.name, str(tag.value)))
                    continue

                res_ann = ann.clone()
                res_meta = image_meta.copy()

                if ASSIGN_AS == "tags":
                    pass
                else:  # metadata
                    res_meta = assign_csv_row_as_metadata(image_meta, csv_row)

                final_ids.append(image_id)
                res_image_name.append(image_name)
                res_anns.append(res_ann)
                res_metas.append(res_meta)





if __name__ == "__main__":
    sly.main_wrapper("main", main)


exit(0)
#
# PROJECT_ID = 1014
# DATASET_ID = 1234
# CSV_DELIMITER = ','
#
# ASSIGN_INFO_TO_IMAGE = True #or False (default True)
#
# csv_index = {}
#
# def normalize_row(row):
#   for key in row:
#     row[key] = row[key].strip()
#
#
#
# def get_matched_row(tags, csv_index):
#   for tag in tags:
#     if tag['name'] == IMAGE_TAG_NAME and tag['value'] is not None and str(tag['value']) in csv_index:
#       return csv_index[tag['value']]
#   return None
#
#
# def get_new_entity_tags(entity_tags, csv_row):
#     cur_tags_exists_dict = set()
#     new_tags = []
#
#     for tag in entity_tags:
#         cur_tags_exists_dict.add(tag['name'])
#
#     for tagName in csv_row:
#         if tagName == CSV_COLUMN_NAME: continue
#         if tagName in cur_tags_exists_dict: continue
#
#         new_tags.append({
#             'name': tagName,
#             'value': csv_row[tagName],
#         })
#     return new_tags
#
#
# def check_project_tags(new_entity_tags, project_tags_by_name, current_project_tags_batch):
#     for tag in new_entity_tags:
#         if tag["name"] not in project_tags_by_name and tag["name"] not in current_project_tags_batch:
#             current_project_tags_batch.add(tag["name"])
#
#
# def generate_colors(count):
#     colors = []
#
#     for _ in range(count):
#         new_color = sly.color.generate_rgb(colors)
#         colors.append(sly.color.rgb2hex(new_color))
#
#     return colors
#
# project_tags = get_list_all_pages(api, "tags.list", {"projectId": PROJECT_ID})
# project_tags_by_name = {}
#
# for tag in project_tags:
#     project_tags_by_name[tag["name"]] = tag
#
# project_tags = None
#
#
# for images_ann in getAnnsIterator(api, {'datasetId': DATASET_ID}):
#   current_project_tags_batch = set()
#   images_tags = []
#   figures_tags = []
#
#     for img_ann in images_ann:
#         cur_img_id = img_ann['imageId']
# #if
#     matched_row = get_matched_row(img_ann['annotation']['tags'], csv_index)
#
#     if matched_row:
#         current_new_tags = get_new_entity_tags(img_ann['annotation']['tags'], matched_row)
#         check_project_tags(current_new_tags, project_tags_by_name, current_project_tags_batch)
#         # if
#     if len(current_project_tags_batch) > 0:
#         colors = generate_colors(len(current_project_tags_batch))
#         tags = []
#
#         for tag_name, color in zip(current_project_tags_batch, colors):
#             tags.append({"name": tag_name,
#                          "color": color,
#                          "settings": {"type": TagValueType.ANY_STRING}
#                          })
#
#         new_project_tags = api.post("tags.bulk.add", {
#             "projectId": PROJECT_ID,
#             "tags": tags
#         }).json()
#
#         for new_tag in new_project_tags:
#             project_tags_by_name[new_tag["name"]] = new_tag
