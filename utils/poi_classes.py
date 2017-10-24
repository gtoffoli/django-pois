from pois.models import Poitype

def import_groups(filename, language='en'):
    """
    import groups:
    groups are listed one per line, without empty lines between them
    example:
    C:\django\roma>python manage.py shell
    >>> import pois.models
    >>> from pois.utils.poi_classes import *
    >>> import_groups(filename="/django/roma/pois/data/os_poi_groups.txt")
    >>> import_groups(filename="/django/roma/pois/data/os_poi_groups.it.txt", language="it")
    """
    f = open(filename)
    for line in f:
        items = line.split()
        code = items[0]
        name = ' '.join(items[1:])
        assert len(code)==2, 'Bad group code: %s' % code
        group = code
        klass = group + '000000'
        if language=='en':
            # entry = Poitype(cgroup=group, name_en=name)
            entry = Poitype(klass=klass, name_en=name)
            entry.save()
        else:
            try:
                # entry = Poitype.objects.get(cgroup=group, category='', klass='')
                entry = Poitype.objects.get(klass=klass)
                setattr(entry, 'name_'+language, name)
                entry.save()
            except:
                pass
    f.close()

def import_categories(filename, language='en'):
    """
    import sets of categories belonging to the same group:
    each set is preceded by a line with the group and followed by an empty line
    example:
    C:\django\roma>python manage.py shell
    >>> import pois.models
    >>> from pois.utils.poi_classes import *
    >>> import_categories(filename="/django/roma/pois/data/os_poi_categories.txt")
    >>> import_categories(filename="/django/roma/pois/data/os_poi_categories.it.txt", language="it")
    """
    f = open(filename)
    next = 'group'
    for line in f:
        if not line:
            next = 'group'
            continue
        items = line.split()
        if not items:
            next = 'group'
            continue
        code = items[0]
        name = ' '.join(items[1:])
        if next=='group':
            group = code
            next = 'category'
        elif next=='category':
            assert len(code)==2, 'Bad category code: %s' % code
            category = code
            klass = group + category + '0000'
            if language=='en':
                # entry = Poitype(cgroup=group, category=category, name_en=name)
                entry = Poitype(klass=klass, name_en=name)
                entry.save()
            else:
                try:
                    # entry = Poitype.objects.get(cgroup=group, category=category, klass='')
                    entry = Poitype.objects.get(klass=klass)
                    setattr(entry, 'name_'+language, name)
                    entry.save()
                except:
                    pass
    f.close()

def import_classes(filename, language='en'):
    """
    import sets of classes belonging to the same category:
    each class is preceded by a line with the category and followed by an empty line
    example:
    C:\django\roma>python manage.py shell
    >>> import pois.models
    >>> from pois.utils.poi_classes import *
    >>> import_classes(filename="/django/roma/pois/data/os_poi_classes.txt")
    >>> import_classes(filename="/django/roma/pois/data/os_poi_classes.it.txt", language="it")
    """
    f = open(filename)
    next = 'category'
    for line in f:
        if not line:
            next = 'category'
            continue
        items = line.split()
        if not items:
            next = 'category'
            continue
        code = items[0]
        name = ' '.join(items[1:])
        if next=='category':
            assert len(code)==2, 'Bad category code'
            category = code
            # group = Poitype.objects.filter(category=category, klass='')[0].cgroup
            category_mask = category + '0000'
            category_klass = Poitype.objects.get(klass__endswith=category_mask).klass
            group = category_klass[:2]
            next = 'klass'
        elif next=='klass':
            assert len(code)==4, 'Bad class code'
            # klass = code
            klass = group + category + code
            if language=='en':
                # entry = Poitype(cgroup=group, category=category, klass=klass, name_en=name)
                entry = Poitype(klass=klass, name_en=name)
                entry.save()
            else:
                try:
                    # entry = Poitype.objects.get(cgroup=group, category=category, klass=klass)
                    entry = Poitype.objects.get(klass=klass)
                    setattr(entry, 'name_'+language, name)
                    entry.save()
                except:
                    pass
    f.close()

        
