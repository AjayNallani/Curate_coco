import argparse, json
import cytoolz
from lxml import etree, objectify
import os, re

'''
usage ----
python3 json2Voc.py --anno_file=/Path/to/instances_train2017.json \
                         --type=instance \
                         --output_dir=/Path/to/classes
'''
def instance2xml_base(anno):
    E = objectify.ElementMaker(annotate=False)
    anno_tree = E.annotation(
        E.folder('VOC2014_instance/{}'.format(anno['category_id'])),
        E.filename(anno['file_name']),
        E.source(
            E.database('MS COCO 2014'),
            E.annotation('MS COCO 2014'),
            E.image('Flickr'),
            E.url(anno['coco_url'])
        ),
        E.size(
            E.width(anno['width']),
            E.height(anno['height']),
            E.depth(3)
        ),
        E.segmented(0),
    )
    return anno_tree


def instance2xml_bbox(anno, bbox_type='xyxy'):
    """bbox_type: xyxy (xmin, ymin, xmax, ymax); xywh (xmin, ymin, width, height)"""
    assert bbox_type in ['xyxy', 'xywh']
    if bbox_type == 'xyxy':
        xmin, ymin, w, h = anno['bbox']
        xmax = xmin+w
        ymax = ymin+h
    else:
        xmin, ymin, xmax, ymax = anno['bbox']
    E = objectify.ElementMaker(annotate=False)
    anno_tree = E.object(
        E.name(anno['category_id']),
        E.bndbox(
            E.xmin(xmin),
            E.ymin(ymin),
            E.xmax(xmax),
            E.ymax(ymax)
        ),
        E.difficult(anno['iscrowd'])
    )
    return anno_tree


def parse_instance(content, outdir):
    categories = {d['id']: d['name'] for d in content['categories']}
    # merge images and annotations: id in images vs image_id in annotations
    merged_info_list = list(map(cytoolz.merge, cytoolz.join('id', content['images'], 'image_id', content['annotations'])))
    # convert category id to name
    for instance in merged_info_list:
        instance['category_id'] = categories[instance['category_id']]
    # group by filename to pool all bbox in same file
    for name, groups in cytoolz.groupby('file_name', merged_info_list).items():
        anno_tree = instance2xml_base(groups[0])
        # if one file have multiple different objects, save it in each category sub-directory
        filenames = []
        for group in groups:
            filenames.append(os.path.join(outdir, re.sub(" ", "_", group['category_id']),
                                    os.path.splitext(name)[0] + ".xml"))
            anno_tree.append(instance2xml_bbox(group, bbox_type='xyxy'))
        for filename in filenames:
            etree.ElementTree(anno_tree).write(filename, pretty_print=True)
        print("Formating instance xml file {} done!".format(name))

def main(args):
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    content = json.load(open(args.anno_file, 'r'))
    if args.type == 'instance':
        # make subdirectories
        sub_dirs = [re.sub(" ", "_", cate['name']) for cate in content['categories']]
        for sub_dir in sub_dirs:
            sub_dir = os.path.join(args.output_dir, str(sub_dir))
            if not os.path.exists(sub_dir):
                os.makedirs(sub_dir)
        parse_instance(content, args.output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anno_file", help="annotation file for object instance/keypoint")
    parser.add_argument("--type", type=str, help="object instance or keypoint", choices=['instance', 'keypoint'])
    parser.add_argument("--output_dir", help="output directory for voc annotation xml file")
    args = parser.parse_args()
    main(args)