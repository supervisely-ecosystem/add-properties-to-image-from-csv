import os
import csv

import supervisely_lib as sly
from supervisely_lib.annotation.tag_meta import TagValueType

#my_app = sly.AppService()

INPUT_FILE = os.environ['INPUT_FILE']

SERVER_ADDRESS = os.environ['SERVER_ADDRESS']
API_TOKEN = os.environ['API_TOKEN']
api = sly.Api(SERVER_ADDRESS, API_TOKEN)


PROJECT_ID = 1014
DATASET_ID = 1234

CSV_DELIMITER = ','

IMAGE_TAG_NAME = "product"
CSV_COLUMN_NAME = "product"


ASSIGN_INFO_TO_IMAGE = True #or False (default True)
ASSIGN_INFO_TO_OBJECTS = True #(default False)

csv_index = {}

def normalize_row(row):
  for key in row:
    row[key] = row[key].strip()

with open(INPUT_FILE, "r") as f_obj:
    reader = csv.DictReader(f_obj, delimiter=CSV_DELIMITER)

    for row in reader:
        normalize_row(row)
        csv_index[row[CSV_COLUMN_NAME]] = row


def getAnnsIterator(api, data):
    first_response = api.post('annotations.list', data).json() #GetOutputMeta
    total = first_response['total'] #imgs
    pages_count = first_response['pagesCount'] #imgs per ann tool page

    if len(first_response['entities']) > 0:    #1 image meta
        yield first_response['entities']

    if pages_count == 1 and len(first_response['entities']) == total:
        pass
    else:
        for page_idx in range(2, pages_count + 1):
            temp_resp = api.post('annotations.list', {**data, 'page': page_idx}).json()

            if len(temp_resp['entities']) > 0:
                yield temp_resp['entities']


def get_matched_row(tags, csv_index):
  for tag in tags:
    if tag['name'] == IMAGE_TAG_NAME and tag['value'] is not None and str(tag['value']) in csv_index:
      return csv_index[tag['value']]

  return None


def get_list_all_pages(api, method, data):
    first_response = api.post(method, data).json()
    total = first_response['total']
    per_page = first_response['perPage']
    pages_count = first_response['pagesCount']

    results = first_response['entities']

    if pages_count == 1 and len(first_response['entities']) == total:
        pass
    else:
        for page_idx in range(2, pages_count + 1):
            temp_resp = api.post(method, {**data, 'page': page_idx, 'per_page': per_page})
            #('annotations.info', {ApiField.IMAGE_ID: image_id, ApiField.WITH_CUSTOM_DATA: with_custom_data})
            temp_items = temp_resp.json()['entities']
            results.extend(temp_items)
        if len(results) != total:
            raise RuntimeError('Method {!r}: error during pagination, some items are missed'.format(method))

    return results

def get_new_entity_tags(entity_tags, csv_row):
    cur_tags_exists_dict = set()
    new_tags = []

    for tag in entity_tags:
        cur_tags_exists_dict.add(tag['name'])


    for tagName in csv_row:
        if tagName == CSV_COLUMN_NAME: continue
        if tagName in cur_tags_exists_dict: continue

        new_tags.append({
            'name': tagName,
            'value': csv_row[tagName],
        })
    return new_tags


def check_project_tags(new_entity_tags, project_tags_by_name, current_project_tags_batch):
    for tag in new_entity_tags:
        if tag["name"] not in project_tags_by_name and tag["name"] not in current_project_tags_batch:
            current_project_tags_batch.add(tag["name"])


def generate_colors(count):
    colors = []

    for _ in range(count):
        new_color = sly.color.generate_rgb(colors)
        colors.append(sly.color.rgb2hex(new_color))

    return colors


project_tags = get_list_all_pages(api, "tags.list", {"projectId": PROJECT_ID})
project_tags_by_name = {}

for tag in project_tags:
    project_tags_by_name[tag["name"]] = tag

project_tags = None


for images_ann in getAnnsIterator(api, {'datasetId': DATASET_ID}):
  current_project_tags_batch = set()
  images_tags = []
  figures_tags = []

  for img_ann in images_ann:
    cur_img_id = img_ann['imageId']
#if
    matched_row = get_matched_row(img_ann['annotation']['tags'], csv_index)

    if matched_row:
        current_new_tags = get_new_entity_tags(img_ann['annotation']['tags'], matched_row)
        check_project_tags(current_new_tags, project_tags_by_name, current_project_tags_batch)
        # if
    if len(current_project_tags_batch) > 0:
        colors = generate_colors(len(current_project_tags_batch))
        tags = []

        for tag_name, color in zip(current_project_tags_batch, colors):
            tags.append({"name": tag_name,
                         "color": color,
                         "settings": {"type": TagValueType.ANY_STRING}
                         })

        new_project_tags = api.post("tags.bulk.add", {
            "projectId": PROJECT_ID,
            "tags": tags
        }).json()

        for new_tag in new_project_tags:
            project_tags_by_name[new_tag["name"]] = new_tag
