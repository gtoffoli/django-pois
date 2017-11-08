'''
Created on 08/lug/2014
@author: giovanni
'''

from haystack import indexes
from pois.models import Poi, Poitype, Odonym, Zone

from django.utils import translation
from django.conf import settings
from haystack.fields import EdgeNgramField

# vedi https://github.com/toastdriven/django-haystack/issues/609
class L10NEdgeNgramFieldField(EdgeNgramField):

    def prepare_template(self, obj):
        translation.activate(settings.LANGUAGE_CODE)
        return super(L10NEdgeNgramFieldField, self).prepare_template(obj)

class PoiIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    slug = indexes.CharField(model_attr='slug', indexed=False)

    def get_model(self):
        return Poi

    def index_queryset(self, using=None):
        qs = self.get_model().objects.filter(state=1)
        if settings.POITYPE_SLUGS:
            poitypes = Poitype.objects.filter(slug__in=settings.POITYPE_SLUGS)
            poi_klasses = [poitype.klass for poitype in poitypes]
            qs = qs.filter(poitype_id__in=poi_klasses)
        return qs

class PoitypeIndex(indexes.SearchIndex, indexes.Indexable):

    text = L10NEdgeNgramFieldField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    slug = indexes.CharField(model_attr='slug', indexed=False)

    def get_model(self):
        return Poitype

    def index_queryset(self, using=None):
        qs = self.get_model().objects.filter(poi_poitype__isnull=False).distinct()
        if settings.POITYPE_SLUGS:
            qs = qs.filter(slug__in=settings.POITYPE_SLUGS)
        return qs

class ZoneIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    slug = indexes.CharField(model_attr='slug', indexed=False)

    def get_model(self):
        return Zone

    def index_queryset(self, using=None):
        zonetypes = [3, 7]
        return self.get_model().objects.filter(zonetype_id__in=zonetypes)

class StreetIndex(indexes.SearchIndex, indexes.Indexable):

    text = indexes.EdgeNgramField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name', indexed=False)
    slug = indexes.CharField(model_attr='slug', indexed=False)

    def get_model(self):
        return Odonym

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(poi_street__isnull=False).distinct()

from django.utils.translation import ugettext_lazy as _
from django import forms
from haystack.forms import ModelSearchForm, model_choices
class poisModelSearchForm(ModelSearchForm):
    def __init__(self, *args, **kwargs):
        super(ModelSearchForm, self).__init__(*args, **kwargs)
        self.fields['models'] = forms.MultipleChoiceField(choices=model_choices(), required=False, label=_('In'), widget=forms.CheckboxSelectMultiple)

from collections import defaultdict
from django.shortcuts import render

q_extra = ['(', ')', '[', ']', '"']
def clean_q(q):
    for c in q_extra:
        q = q.replace(c, '')
    return q

def navigation_autocomplete(request, template_name='pois/autocomplete.html'):
    q = request.GET.get('q', '')
    q = clean_q(q)
    context = {'q': q}
    if settings.USE_HAYSTACK:
        from haystack.query import SearchQuerySet
        MAX = 16
        results = SearchQuerySet().filter(text=q)
        if results.count()>MAX:
            results = results[:MAX]
            context['more'] = True
        queries = defaultdict(list)
        for result in results:
            klass = result.model.__name__
            values_list = [result.get_stored_fields()['name'], result.get_stored_fields()['slug']]
            queries[klass].append(values_list)
    context.update(queries)
    return render(request, template_name, context)