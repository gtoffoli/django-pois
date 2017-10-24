from __future__ import unicode_literals

# Add before admin.autodiscover() and any form import for that matter:
"""
MMR temporaneamente disattivato
import autocomplete_light
autocomplete_light.autodiscover()
"""

from dal import autocomplete

from django import forms
from django.forms import ModelForm
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import string_concat

from django.contrib.auth.models import User
from django.contrib.admin.widgets import FilteredSelectMultiple
# from django.contrib.gis.forms.fields import GeometryField
from django.contrib.gis.admin.widgets import OpenLayersWidget
from tinymce.widgets import TinyMCE
from captcha.fields import CaptchaField, CaptchaTextInput

"""
MMR temporaneamente disattivato
from richtext_blog.models import Post, Tag as BlogTag
from richtext_blog.forms import CommentForm
"""
from pois.models import Zonetype, Zone, Route, Tag, Poitype, Poi, Odonym # MMR temporaneamente disattivato - , Blog
# from pois.utils.gmap_widget import GoogleMapsWidget

"""
MMR temporaneamente disattivato
autocomplete_light.register(User, search_fields=['username', 'first_name', 'last_name',])
autocomplete_light.register(Zone)
autocomplete_light.register(Route)
autocomplete_light.register(Odonym)
# autocomplete_light.register(Tag, search_fields=['name_it'])
autocomplete_light.register(Tag, search_fields=['name'])
# autocomplete_light.register(Poitype, search_fields=['name_it'])
autocomplete_light.register(Poitype, search_fields=['name'])
autocomplete_light.register(Poi)
"""

class ZoneForm(ModelForm):

    description = forms.CharField(required=False,widget=TinyMCE())
    zones = forms.ModelMultipleChoiceField(
        label="Vedi anche",
        queryset=Zone.objects.order_by('zonetype', 'id'), 
        required=False,
        widget=FilteredSelectMultiple("Vicini:", False, attrs={'rows': 4}))
    careof = forms.ModelChoiceField(queryset=Poi.objects.all(),
        required=False,
        label='A cura di',
        # widget=autocomplete_light.ChoiceWidget(autocomplete='PoiAutocomplete',
        #    attrs={'minimum_characters': 3,
        #                                'placeholder': 'Scegli risorsa'})

        )

    class Meta:
        model = Zone
        fields = (
            'code',
            'name',
            'zonetype',
            'pro_com',
            'slug',
            'short',
            'description',
            'geom',
            'zones',
            'web',
        )
        widgets = {
            """
            'name': forms.TextInput(attrs={'size':'80'}),
            'slug': forms.TextInput(attrs={'size':'80'}),
            'short': forms.TextInput(attrs={'size':'120'}),
            """
            #'description': forms.Textarea(attrs={'cols': 60, 'rows': 3}),
            'description': forms.CharField(required=False,widget=TinyMCE()),
            'zones': FilteredSelectMultiple("Vicini:", False, attrs={'rows': 4}),
            'web': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
       }


class RouteForm(ModelForm):

    description = forms.CharField(required=False,widget=TinyMCE())

    class Meta:
        model = Route
        fields = (
            'code',
            'name',
            'slug',
            'short',
            'description',
            'coords',
            'geom',
            'web',
            'state',
        )
        widgets = {
            'description': forms.CharField(required=False,widget=TinyMCE()),
            'zones': FilteredSelectMultiple("Vicini:", False, attrs={'rows': 4}),
            'web': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'coords': forms.Textarea(attrs={'cols': 60, 'rows': 6}),
       }

# from django.conf import settings
# poi_categories = settings.POI_CATEGORIES

zonetype_ids = [1, 3, 2]
zone_groups = []
for zonetype_id in zonetype_ids:
    zonetype = Zonetype.objects.get(id=zonetype_id)
    # MMR old version - group_label = unicode(zonetype)
    group_label = zonetype
    option_group = []
    for zone in Zone.objects.filter(zonetype=zonetype).order_by('id'):
        zone_id = zone.id
         # MMR old version - label = unicode(zone)
        label = zone
        option_group.append((zone_id, label))
    zone_groups.append((group_label, option_group))

def make_zone_widget(value):
    zone_list = []
    zone_list.append('<select class="selector" id="id_zone" name="zone">')
    zone_list.append('<option value="">---------</option>')
    for group in zone_groups:
        group_label = group[0]
        options = group[1]
        zone_list.append('<optgroup label="%s">' % group_label)
        for option in options:
            zone_id = option[0]
            label = option[1]
            selected = (zone_id==value) and 'selected' or ''
            zone_list.append('<option value="%s" %s>%s</option>' % (zone_id, selected, label))
        zone_list.append('</optgroup>')
    zone_list.append('</select>')
    zone_widget = '\n'.join(zone_list)
    return zone_widget

poitype_groups = []
for group in Poitype.objects.filter(klass__endswith='0000'):
    category = group.klass
    # if category not in poi_categories:
    if not group.active:
        continue
    # MMR old version - group_label = unicode(group)
    group_label = group
    option_group = []
    for pt in Poitype.objects.filter(klass__startswith=category[:4]):
        klass = pt.klass
        if klass == category:
            continue
        if not pt.active:
            continue
        # MMR old version - label = unicode(pt)
        label = pt
        option_group.append((klass, label))
        # option_group.append((pt.id, label))
    poitype_groups.append((group_label, option_group))

def make_poitype_widget(value):
    poitype_list = []
    poitype_list.append('<select class="selector" id="id_poitype" name="poitype">')
    poitype_list.append('<option value="">---------</option>')
    for group in poitype_groups:
        group_label = group[0]
        options = group[1]
        poitype_list.append(u'<optgroup label="%s">' % group_label)
        for option in options:
            klass = option[0]
            label = option[1]
            selected = (klass==value) and 'selected' or ''
            poitype_list.append('<option value="%s" %s>%s</option>' % (klass, selected, label))
        poitype_list.append('</optgroup>')
    poitype_list.append('</select>')
    poitype_widget = '\n'.join(poitype_list)
    return poitype_widget

class PoitypeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "My Object #%i" % obj.id

from django.utils.html import mark_safe
class PoitypeSelectWidget(forms.widgets.Select):
    def render(self, name, value, attrs=None, choices=()):
        # output = forms.Select.render(self, name, value, attrs=attrs, choices=poitype_groups)
        # output = forms.Select.render(self, name, value, attrs=attrs)
        # output = poitype_widget
        output = make_poitype_widget(value)
        # print output
        return mark_safe(output)

"""
MMR temporaneamente disattivato
class AutocompleteRelatedPoiItems(autocomplete_light.AutocompleteGenericBase):
    choices = (
        Poi.objects.all(),
    )
    search_fields = (
        ('name',),
    )
autocomplete_light.register(AutocompleteRelatedPoiItems)
"""

class PoiWidget(OpenLayersWidget):
    """ subclasses default widget for form field GeometryField """
    def render(self, name, value, attrs=None):
        OpenLayersWidget.render(self, name, value, attrs=attrs)

COMUNE_CHOICES = [(58091, 'Roma')] + [(zone.pro_com, zone.name) for zone in Zone.objects.filter(zonetype_id=7, pro_com__isnull=False).exclude(pro_com=58091).order_by('name')]

# Create the form class.
# class PoiForm(ModelForm):


# MMR old version - class PoiForm(autocomplete_light.GenericModelForm):
class PoiForm(ModelForm):
    """
    poitype = forms.ChoiceField(label="Tipo di risorsa", choices=(),
                                       widget=forms.Select(attrs={'class':'selector'}))
    """
    name = forms.TextInput(attrs={'size':'80'})
    othertags = forms.TextInput(attrs={'size':'80'})
    """
    phone = forms.Textarea(attrs={'cols': 60, 'rows': 2})
    email = forms.Textarea(attrs={'cols': 60, 'rows': 2})
    web = forms.Textarea(attrs={'cols': 60, 'rows': 2})
    notes = forms.Textarea(attrs={'cols': 60, 'rows': 3})
    """
    poitype = forms.ModelChoiceField(
        label="Categoria primaria",
        queryset=Poitype.objects.all(),
        to_field_name='klass',
        widget=PoitypeSelectWidget(attrs={'class':'selector'}))
    """
    moretypes = forms.ModelMultipleChoiceField(Poitype.objects.all(),
        required=False,
        label="Categorie secondarie",
        widget=autocomplete_light.MultipleChoiceWidget(autocomplete='PoitypeAutocomplete',
            attrs={'minimum_characters': 3,
                                        'placeholder': 'Aggiungi categoria'}))
    """
    description = forms.CharField(required=False,widget=TinyMCE())
    """
    host_object = autocomplete_light.GenericModelChoiceField(
                required=False,
                label='Ospitata da',
                widget=autocomplete_light.ChoiceWidget(autocomplete='AutocompleteHostPoiItems',
                    attrs={'minimum_characters': 3,
                    'placeholder': 'Scegli risorsa'}))
    """
    host = forms.ModelChoiceField(Poi.objects.all(),
        required=False,
        label='Ospitata da',
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.ChoiceWidget(autocomplete='PoiAutocomplete',
        #    attrs={'minimum_characters': 3,
        #                                'placeholder': 'Scegli risorsa'})
        )
    pois = forms.ModelMultipleChoiceField(Poi.objects.all(),
        required=False,
        label='Risorse correlate',
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.MultipleChoiceWidget('PoiAutocomplete',
        #    attrs={'minimum_characters': 3,
        #                               'placeholder': 'Aggiungi risorsa'})
        )
    tags = forms.ModelMultipleChoiceField(Tag.objects.all(),
        required=False,
        label='Aree tematiche',
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.MultipleChoiceWidget('TagAutocomplete',
        #    attrs={'minimum_characters': 3,
        #                               'placeholder': 'Aggiungi area tematica'})
        )
    zones = forms.ModelMultipleChoiceField(Zone.objects.all(),
        required=False,
        label="Zone",
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.MultipleChoiceWidget(autocomplete='ZoneAutocomplete',
        #    attrs={'minimum_characters': 3,
        #                                'placeholder': 'Aggiungi zona'})
        )
    routes = forms.ModelMultipleChoiceField(Route.objects.all(),
        required=False,
        label="Route",
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.MultipleChoiceWidget(autocomplete='RouteAutocomplete',
        #   attrs={'minimum_characters': 3,
        #                               'placeholder': 'Aggiungi itinerario'})
        )
    pro_com = forms.ChoiceField(choices=COMUNE_CHOICES,
        required=False,
        label='Comune')

    street = forms.ModelChoiceField(Odonym.objects.all(),
        required=False,
        label='Via o Piazza o ..',
        widget=autocomplete.ModelSelect2(url='toponimo-autocomplete/', attrs={'style': 'width: 80%;'})
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.ChoiceWidget(autocomplete='OdonymAutocomplete',
        #    attrs={'minimum_characters': 3,
        #                               'placeholder': 'Scegli via o ..'})
        )
    # point = GeometryField(widget=PoiWidget())
    """
    source = forms.ModelChoiceField(Poi.objects.all(),
        required=False,
        label='Fonte (risorsa)',
        widget=autocomplete_light.ChoiceWidget(autocomplete='PoiAutocomplete',
            attrs={'minimum_characters': 3,
                                        'placeholder': 'Scegli risorsa'}))
    """
    careof = forms.ModelChoiceField(Poi.objects.all(),
        required=False,
        label='A cura di',
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.ChoiceWidget(autocomplete='PoiAutocomplete',
        #   attrs={'minimum_characters': 3,
        #                               'placeholder': 'Scegli risorsa'})
        )
    members = forms.ModelMultipleChoiceField(User.objects.all(),
        required=False,
        label='Membri (utenti)',
        # MMR temporaneamente disattivato
        # widget=autocomplete_light.MultipleChoiceWidget('UserAutocomplete',
        #   attrs={'minimum_characters': 3,
        #                               'placeholder': 'Aggiungi membro'})
        )

    class Meta:
        model = Poi
        fields = (
            'name',
            'kind', # aggiunto 130808
            'poitype',
            # 'moretypes', # aggiunto 130620, rimosso 130808
            'slug',
            'host', # was 'host_object',
            'pois',
            'tags',
            'zones',
            'routes',
            'short',
            'description',
            # 'othertags', # rimosso 130808
            'pro_com',
            'street_address',
            'street', # was 'street_object', # was 'content_object',
            'housenumber',
            'zipcode',
            'latitude',
            'longitude',
            'point',
            'phone',
            'email',
            'web',
            'video',
            'feeds',
            'logo',
            'notes',
            'sourcetype',
            'source',
            # 'sourceel',
            # 'sourceid',
            # 'creator',
            'owner',
            # 'contributor',
            'careof', # aggiunto 130808
            'state', # aggiunto 130808
            'partnership', # aggiunto 130808
            'members', # aggiunto 130808
        )
        widgets = {
            # 'name': forms.TextInput(attrs={'size':'80'}),
            # 'othertags': forms.TextInput(attrs={'size':'80'}),
            'phone': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'email': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'web': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'video': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'feeds': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'notes': forms.Textarea(attrs={'cols': 60, 'rows': 3}),
        }
 
# MMR old version - class PoiUserForm(autocomplete_light.GenericModelForm):
class PoiUserForm(ModelForm):
    """
    error_css_class = 'error'
    required_css_class = 'required'
    """
    class Meta:
        model = Poi
        fields = ('name', 'short', 'tags', 'street', 'housenumber', 'zipcode', 'phone', 'email', 'web', 'video', 'description', 'notes',)

    name = forms.CharField(
            label=_("Name of the resource"),
            required=True,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    short = forms.CharField(
            label=_("Type of resource"),
            required=True,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    tags = forms.ModelMultipleChoiceField(Tag.objects.all().exclude(id=49),
            label=_('Theme areas'),
            help_text=_("Choose 1 or 2 theme areas"),
            required=True,
            widget=forms.CheckboxSelectMultiple())
    street = forms.ModelChoiceField(queryset=Odonym.objects.all(),
            label=_('Street name'),
            help_text=_("Enter at least 3 characters of the name, wait for some suggestions and choose one"),
            required=True,
            widget=autocomplete.ModelSelect2(url='toponimo-autocomplete', attrs={'style': 'width: 80%;'})

            # MMR temporaneamente disattivato
            #widget=autocomplete_light.ChoiceWidget(autocomplete='OdonymAutocomplete',
            #   attrs={'minimum_characters': 3, 'placeholder': 'Enter a few characters and choose'})
            )
    housenumber = forms.CharField(
            label=_("House number"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    zipcode = forms.CharField(
            label=_("Zipcode"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    phone = forms.CharField(
            label=_("Phone"),
            required=False,
            widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2, 'cols': 60}))
    email = forms.EmailField(
            label=_("Email"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    web = forms.URLField(
            label=_("Web"),
            required=False,
            widget=forms.TextInput(attrs={'class': 'form-control'}))
    video = forms.URLField(
            label=_("Youtube"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control',}))
    description = forms.CharField(
            label=_('Description'),
            required=False,
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'cols': 60}))
    notes = forms.CharField(
            label=_("Notes"),
            help_text=_("If you aren't a registered user, please enter here your contact data: Full name, Email and/or Phone"),
            required=False,
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'cols': 60}))
    captcha = CaptchaField(
            label=_("Control string"),
            help_text=_("Enter these 5 characters in the textbox on the right"),
            widget=CaptchaTextInput(attrs={'class': 'form-control'})
            )
    """
    class Meta:
        model = Poi
        fields = (
            'name',
            'short',
            'tags',
            'street',
            'housenumber',
            'zipcode',
            'phone',
            'email',
            'web',
            'notes',
        )
        widgets = {
            'phone': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'email': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'web': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'notes': forms.Textarea(attrs={'cols': 60, 'rows': 3}),
        }
    """

class PoiBythemeForm(forms.Form):
    """
    MMMR
    error_css_class = 'error'
    required_css_class = 'required'
    """
    
    """
    def __init__(self, *args, **kwargs):
        tags = kwargs.pop('tags')
        super(PoiBythemeForm, self).__init__(*args,**kwargs)
        self.fields['tags'].initial = tags
    """
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.exclude(pk=49),
            # label=_('Theme areas'),
            label=_("Choose theme areas"),
            help_text=_("Choose theme areas"),
            required=False,
            widget=forms.CheckboxSelectMultiple(),)

class PoiSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        q = kwargs.get('q', '')
        if q:
            kwargs.pop('q')
        super(PoiSearchForm, self).__init__(*args,**kwargs)
        if q:
            self.fields['q'].initial = q

    what = forms.MultipleChoiceField(
        label=_("what to search"),
        required=False,
        choices = (('resources', _('resources')), ('categories', _('categories')), ('zones', _('zones')), ('streets', _('streets')),),
        initial=('resources', 'categories', 'zones', 'streets'),
        widget=forms.CheckboxSelectMultiple(),)
    q = forms.CharField(
        label=_("text to match"),
        required=False,
        widget=forms.TextInput())
    text_in = forms.MultipleChoiceField(
        label=_('match text in'),
        required=False,
        # choices = (('name', _('name')), ('short', _('short description')), ('other', _('other')),),
        choices = (('name', _('name')), ('short', _('short description')),),
        initial=('name', 'short',),
        widget=forms.CheckboxSelectMultiple(),)
    tags = forms.ModelMultipleChoiceField(Tag.objects.all(),
        label=_('theme areas'),
        help_text=_("Choose theme areas (no selection = all areas)"),
        required=False,
        widget=forms.CheckboxSelectMultiple(),)

class PoiAnnotationForm(forms.Form):
    error_css_class = 'error'
    required_css_class = 'required'

    """
    def __init__(self, *args, **kwargs):
        if kwargs:
            poi_id = kwargs.pop('poi_id')
        else:
            poi_id = args[0]['id']
        super(PoiAnnotationForm, self).__init__(*args,**kwargs)
        self.fields['id'].initial = poi_id
    """

    id = forms.IntegerField(widget=forms.HiddenInput, required=False) 
    notes = forms.CharField(
            label=_("Notes"),
            help_text= string_concat(_("If you aren't a registered user"), " ", _("please"), " ", _("add"), " ", _("your contact data: Full name, Email and/or Phone")),
            required=True,
            widget=forms.Textarea(attrs={'class':'span6', 'cols': 60, 'rows': 3}))
    captcha = CaptchaField(
            label=_("Control string"),
            help_text=_("Enter these 5 characters in the textbox on the right"),
            required=True,)

"""
MMMR temporaneamente disattivato
zonetypes_with_blogs = [0, 3]
class AutocompleteBlogHostItems(autocomplete_light.AutocompleteGenericBase):
    choices = (
        Zone.objects.filter(zonetype__in=zonetypes_with_blogs),
        Poi.objects.all(),
    )
    search_fields = (
        ('name',),
        ('name',),
    )
autocomplete_light.register(AutocompleteBlogHostItems)

class BlogForm(autocomplete_light.GenericModelForm):
    host_object = autocomplete_light.GenericModelChoiceField(
                label='Ospitato da (zona o risorsa)', help_text='type in a few chars',
                widget=autocomplete_light.ChoiceWidget(autocomplete='AutocompleteBlogHostItems'))

    class Meta:
        model = Blog
        fields = (
            'title',
            'slug',
            'author',
            'host_object',
            'description',
            'state',
        )

class BlogUserForm(ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'

    class Meta:
        model = Blog
        exclude = ('slug', 'author', 'host_type', 'host_id')

class MultipleSelectWithPop(forms.SelectMultiple):
    def render(self, name, *args, **kwargs):
        html = super(MultipleSelectWithPop, self).render(name, *args, **kwargs)
        popupplus = render_to_string("richtext_blog/popup_plus.html", {'field': name})
        return html+popupplus
 
class PostUserForm(ModelForm):
    error_css_class = 'error'
    required_css_class = 'required'

    def __init__(self, *args, **kwargs):
        post_id = None
        if kwargs.get('instance'):
            post_id = kwargs.get('instance')
        blog_id = None
        if kwargs.get('blog_id'):
            blog_id = kwargs.pop('blog_id')
        super(PostUserForm, self).__init__(*args,**kwargs)
        if post_id:
            self.fields['id'].initial = post_id
        if blog_id:
            self.fields['blog'].initial = blog_id

    id = forms.IntegerField(widget=forms.HiddenInput, required=False) 
    # author = forms.ModelChoiceField(User.objects.all(), widget=forms.HiddenInput)
    blog = forms.ModelChoiceField(Blog.objects.all(), widget=forms.HiddenInput)
    tags = forms.ModelMultipleChoiceField(BlogTag.objects.all(), widget=MultipleSelectWithPop)
    content = forms.CharField(required=False, widget=TinyMCE())

    class Meta:
        model = Post
        exclude = ('slug', 'author',)

#add new tag pop-up
class TagUserForm(ModelForm):

    class Meta:
        model = BlogTag
        fields = ['name']


def CommentForm_init(self, *args, **kwargs):
    super(CommentForm, self).__init__(*args, **kwargs)
    self.fields['author'].label = _("Author")
    self.fields['comment'].label = _("Comment")
    self.fields['verification'].label = _("Verification")
    self.fields['verification'].help_text = _("Please type the letters in the image")

CommentForm.__init__ = CommentForm_init

"""