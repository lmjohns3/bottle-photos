import datetime
import lmj.cli
import lmj.photos
import os
import sys
import traceback

cmd = lmj.cli.add_command('retag')
cmd.add_argument('--replace', action='store_true',
                 help='replace existing tags')
cmd.add_argument('--exif', action='store_true',
                 help='reload and replace EXIF tags from source')
cmd.add_argument('--add', default=[], nargs='+', metavar='TAG',
                 help='add these TAGs to all selected photos')
cmd.add_argument('--add-path-tag', action='store_true',
                 help='use the parent DIR as a tag for each import')
cmd.add_argument('tag', nargs='+', metavar='TAG',
                 help='retag only photos with these TAGs')
cmd.set_defaults(mod=sys.modules[__name__])

logging = lmj.cli.get_logger(__name__)


def main(args):
    photos = list(lmj.photos.find_tagged(args.tag))
    for p in photos:
        tags = list(args.add)
        if args.add_path_tag:
            tags.append(os.path.basename(os.path.dirname(p.path)))
        if not args.replace:
            tags.extend(p.user_tag_set)
        tags = [t.strip().lower() for t in tags if t.strip()]

        p.meta['user_tags'] = sorted(set(tags))
        if args.exif:
            p.meta['exif_tags'] = lmj.photos.tags_from_exif(p.exif)

        logging.info('%s: user: %s; exif: %s',
                     os.path.basename(p.path),
                     ', '.join(p.meta['user_tags']),
                     ', '.join(p.meta['exif_tags']),
                     )

        lmj.photos.update(p)
