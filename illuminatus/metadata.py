import arrow
import os
import re

# Names of camera models, these will be filtered out of the metadata tags.
_CAMERA_WORD_BLACKLIST = 'canon nikon kodak digital camera super powershot'.split()

# EXIF tags where we should look for timestamps.
_TIMESTAMP_KEYS = 'DateTimeOriginal CreateDate ModifyDate FileModifyDate'.split()
_TIMESTAMP_FORMATS = ['YYYY-MM-DD HH:mm:ss', 'YYYY:MM:DD HH:mm:ss']

# Pattern for matching a floating-point number.
_FLOAT_PATTERN = r'(\d+)(\.\d+)?'


def get_timestamp(path, meta):
    '''Get the timestamp for an asset based on metadata or file mtime.

    Parameters
    ----------
    path : str
        File path for the asset.
    meta : dict
        Metadata values for the asset

    Returns
    -------
    An `arrow` datetime object.
    '''
    if meta:
        for key in _TIMESTAMP_KEYS:
            stamp = meta.get(key)
            if stamp is not None:
                try:
                    return arrow.get(stamp, _TIMESTAMP_FORMATS)
                except ValueError:
                    pass
    try:
        return arrow.get(os.path.getmtime(path))
    except FileNotFoundError:
        pass
    return arrow.get('1000-01-01 00:00:00')


def _round_to_most_significant_digits(n, digits=1):
    '''Return n rounded to the most significant `digits` digits.'''
    nint = n
    if isinstance(nint, float):
        nint = int(nint)
    if not isinstance(nint, int):
        match = re.match(r'^(\d+).*$', n)
        if match:
            nint = int(match.group(1))
        else:
            raise ValueError(n)
    if nint < 10 ** digits:
        return nint
    shift = 10 ** (len(str(n)) - digits)
    return int(shift * round(nint / shift))


def gen_metadata_tags(meta):
    '''Generate a set of metadata tags.

    Parameters
    ----------
    meta : dict
        A dictionary mapping metadata fields to values.

    Yields
    ------
    A :class:`Tag`s derived from the given metadata.
    '''
    if not meta:
        return

    highest = _round_to_most_significant_digits

    model = meta.get('CameraModelName', meta.get('Model', '')).lower()
    for pattern in _CAMERA_WORD_BLACKLIST + ['ed$', 'is$']:
        model = re.sub(pattern, '', model).strip()
    if model:
        yield 'kit:{}'.format(model).lower()

    fstop = meta.get('FNumber', '')
    if isinstance(fstop, (int, float)) or re.match(_FLOAT_PATTERN, fstop):
        yield 'aperture:f/{}'.format(round(10 * float(fstop)) / 10).replace('.0', '')

    mm = meta.get('FocalLengthIn35mmFormat', meta.get('FocalLength', ''))
    if isinstance(mm, str):
        match = re.match(_FLOAT_PATTERN + r'\s*mm', mm)
        mm = match.group(1) if match else None
    if mm:
        yield 'focus:{}mm'.format(highest(mm))


def gen_datetime_tags(stamp):
    '''Build a set of datetime tags.

    Parameters
    ----------
    stamp : `arrow.Arrow`
        Timestamp for constructing tags.

    Yields
    ------
    Tag strings derived from the timestamp.
    '''
    if not stamp:
        return

    # 2009
    yield 'y:{:04d}'.format(stamp.year)

    # january
    yield 'm:{:02d}:{}'.format(stamp.month, stamp.format('MMMM')).lower()

    # 22nd
    yield 'd:{:02d}:{}'.format(stamp.day, stamp.format('Do')).lower()

    # monday
    yield 'w:{}:{}'.format(stamp.weekday(), stamp.format('dddd')).lower()

    # for computing the hour tag, we set the hour boundary at 49-past, so
    # that any time from, e.g., 10:49 to 11:48 gets tagged as "11am"
    hour = stamp.shift(minutes=11)
    yield 'h:{:02d}:{}'.format(hour.hour, hour.format('ha')).lower()