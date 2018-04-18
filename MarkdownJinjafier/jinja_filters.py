from dateutil import parser as dateparser
import datetime, pypandoc, re, json

def j2_strftime(date):
    date = dateparser.parse(date)
    native = date.replace(tzinfo=None)
    format = '%B %d, %Y'
    return native.strftime(format)

def j2_sortkeys(keys):
    def get_year(k):
        nums = re.sub('[^0-9]', '', k)
        nums = nums[-4:]
        # logging.debug(nums)
        return nums

    keys.sort(key=get_year, reverse=True)
    return keys


def j2_bystart(items, reverse=False):
    items.sort(key=lambda k: k['startdate'] or k['enddate'], reverse=reverse)
    return items


def j2_ongoing(items):
    """
    Returns list of items with no enddate, or enddate in the future
    """
    # logging.debug(items)
    ret = []
    for item in items:
        if not item.get('enddate') or \
                item['enddate'] > datetime.datetime.now().date():
            ret.append(item)
    return ret


def j2_completed(items):
    """
    Returns list of items with enddate in the past
    """
    # logging.debug(items)
    ret = []
    for item in items:
        if item.get('enddate') and \
                item['enddate'] < datetime.datetime.now().date():
            ret.append(item)
    return ret

