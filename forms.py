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
from pois.models import Zonetype, Zone, Route, Tag, Poitype, Poi, Odonym, Confighome #MMR temporaneamente disattivato - , Blog
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
class PoitypeForm(ModelForm):
    name_en = forms.CharField(widget=forms.TextInput(attrs={'style':'width:40em','maxlength':80}))
    name = forms.CharField(widget=forms.TextInput(attrs={'style':'width:40em','maxlength':80}))
    slug = forms.CharField(widget=forms.TextInput(attrs={'style':'width:40em','maxlength':50}))
    #short = forms.CharField(widget=forms.TextInput(attrs={'style':'width:80em','maxlength':120}))

    class Meta:
        model = Poitype
        fields = (
            'klass',
            'name_en',
            'name',
            'slug',
            'icon',
            'color',
            'tags'
        )

class TagForm(ModelForm):
    name_en = forms.CharField(widget=forms.TextInput(attrs={'style':'width:40em','maxlength':40}))
    name = forms.CharField(widget=forms.TextInput(attrs={'style':'width:40em','maxlength':40}))
    slug = forms.CharField(widget=forms.TextInput(attrs={'style':'width:40em','maxlength':50}))
    short = forms.CharField(widget=forms.TextInput(attrs={'style':'width:80em','maxlength':120}))

    class Meta:
        model = Tag
        fields = (
            'name_en',
            'name',
            'slug',
            'short',
            'weight',
            'color',
            'tags'
        )
class ZoneForm(ModelForm):

    description = forms.CharField(required=False,widget=TinyMCE())
    zones = forms.ModelMultipleChoiceField(
        label="Vedi anche",
        queryset=Zone.objects.order_by('zonetype', 'id'), 
        required=False,
        widget=FilteredSelectMultiple("Vicini:", False, attrs={'rows': 4})
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
    name = forms.CharField(widget=forms.TextInput(attrs={'style':'width:50em','maxlength':100}))
    short = forms.CharField(widget=forms.TextInput(attrs={'style':'width:60em','maxlength':120}))
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
        widget=autocomplete.ModelSelect2(url='risorsa-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli risorsa','style':'width:60%'})
        )
    pois = forms.ModelMultipleChoiceField(Poi.objects.all(),
        required=False,
        label='Risorse correlate',
        widget=autocomplete.ModelSelect2Multiple(url='risorsa-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli risorsa', 'style':'width:60%'})
        )
    tags = forms.ModelMultipleChoiceField(Tag.objects.all(),
        required=False,
        label='Aree tematiche',
        widget=autocomplete.ModelSelect2Multiple(url='tema-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Aggiungi area tematica', 'style':'width:60%'})
        )
    zones = forms.ModelMultipleChoiceField(Zone.objects.all(),
        required=False,
        label="Zone",
        widget=autocomplete.ModelSelect2Multiple(url='zona-autocomplete', attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Aggiungi zona', 'style':'width:60%'})
        )
    routes = forms.ModelMultipleChoiceField(Route.objects.all(),
        required=False,
        label="Route",
        widget=autocomplete.ModelSelect2Multiple(url='itinerario-autocomplete', attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Aggiungi itinerario', 'style':'width:60%'})
        )
    pro_com = forms.ChoiceField(choices=COMUNE_CHOICES,
        required=False,
        label="Comune")
    street_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'style':'width:50em','maxlength':100}))
    street = forms.ModelChoiceField(Odonym.objects.all(),
        required=False,
        label='Via o Piazza o ..',
        widget=autocomplete.ModelSelect2(url='toponimo-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli via o ..'})
        )
    owner = forms.ModelChoiceField(User.objects.all(),
        required=False,
        label='Proprietario',
        widget=autocomplete.ModelSelect2(url='utente-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli proprietario'})
        )
    careof = forms.ModelChoiceField(Poi.objects.all(),
        required=False,
        label='A cura di',
        widget=autocomplete.ModelSelect2(url='risorsa-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli risorsa', 'style':'width:30%'})
        )
    members = forms.ModelMultipleChoiceField(User.objects.all(),
        required=False,
        label='Membri (utenti)',
        widget=autocomplete.ModelSelect2Multiple(url='utente-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Aggiungi membro', 'style':'width:30%'})
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
            'typecard', # MMR aggiunto 180405
        )
        widgets = {
            'phone': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'email': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'web': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'video': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'feeds': forms.Textarea(attrs={'cols': 60, 'rows': 2}),
            'notes': forms.Textarea(attrs={'cols': 60, 'rows': 3}),
        }

class PoiUserForm(ModelForm):

    class Meta:
        model = Poi
        # fields = ('name', 'short', 'tags', 'pro_com', 'street', 'street_address', 'housenumber', 'zipcode', 'phone', 'email', 'web', 'facebook', 'video', 'description',)
        fields = ('name', 'short', 'tags', 'pro_com', 'street', 'street_address', 'housenumber', 'zipcode', 'phone', 'email', 'web', 'facebook',)

    name = forms.CharField(
            label=_("name of the resource"),
            required=True,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    short = forms.CharField(
            label=_("short description"),
            required=True,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    tags = forms.ModelMultipleChoiceField(Tag.objects.all().exclude(id=49),
            label=_('theme areas'),
            help_text=_("Choose 1 or 2 theme areas"),
            required=True,
            widget=forms.CheckboxSelectMultiple())
    pro_com = forms.ChoiceField(choices=COMUNE_CHOICES,
            required=False,
            label=_('town'),
            widget=forms.Select(attrs={'class':'form-control','style':'width:20em',}))
    street = forms.ModelChoiceField(queryset=Odonym.objects.all(),
            label='Roma: %s' % (_('street name')),
            help_text=_("Enter at least 3 characters of the name, wait for some suggestions and choose one"),
            required=False,
            widget=autocomplete.ModelSelect2(url='toponimo-autocomplete', attrs={'data-minimum-input-length': 3,'data-placeholder': _('Selected ROMA: enter the street here')})
            )
    street_address = forms.CharField(
            required=False,
            label='%s: %s' % (_('Other town'), _('street name')),
            widget=forms.TextInput(attrs={'class':'form-control','maxlength':100, 'placeholder':_('If you have chosen ANOTHER TOWN, enter the street here')}))
    housenumber = forms.CharField(
            label=_("house number"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control',}))
    zipcode = forms.CharField(
            label=_("zipcode").title(),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control',}))
    phone = forms.CharField(
            label=_("phone"),
            required=False,
            widget=forms.Textarea(attrs={'class':'form-control', 'rows': 2, 'cols': 60}))
    email = forms.EmailField(
            label=_("email"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    web = forms.URLField(
            label=_("web"),
            required=False,
            widget=forms.TextInput(attrs={'class': 'form-control'}))
    facebook = forms.URLField(
            label=_("facebook"),
            required=False,
            widget=forms.TextInput(attrs={'class': 'form-control'}))
    """
    video = forms.URLField(
            label=_("youtube"),
            required=False,
            widget=forms.TextInput(attrs={'class':'form-control',}))
    description = forms.CharField(
            label=_('description'),
            required=False,
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'cols': 60}))
    notes = forms.CharField(
            label=_("Notes"),
            help_text="",
            required=False,
            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'cols': 60}))
    """
    fullname = forms.CharField(
            label=_("Full Name"),
            help_text=_("If you aren't a connected user, please enter here Full Name"),
            required=True,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    user_email = forms.EmailField(
            label=_("your email"),
            help_text=_("If you aren't a connected user, please enter here your email"),
            required=True,
            widget=forms.TextInput(attrs={'class':'form-control'}))
    permission = forms.BooleanField(required=True, label=_('Pursuant to art. 13 of Legislative Decree 30 June 2003 n. 196 we wish to inform you that the personal data supplied by You with the compilation and submission of this form will only serve to have a contact for this report.'), widget=forms.CheckboxInput())
    captcha = CaptchaField(
            label=_("control string"),
            help_text=_("Enter these 5 characters in the textbox on the right"),
            widget=CaptchaTextInput(attrs={'class': 'form-control'})
            )

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        if len(tags) > 2:
            raise forms.ValidationError(_('Too many thematic areas chosen.'), code='invalid')
        return tags
    
    def clean_street(self):
        pro_com = self.cleaned_data['pro_com']
        if (pro_com == str(COMUNE_CHOICES[0][0])):
            street = self.cleaned_data['street']
            if street == None:
                raise forms.ValidationError(_('This field is required.'), code='required')
            return street
    
    def clean_street_address(self):
        pro_com = self.cleaned_data['pro_com']
        if (pro_com != str(COMUNE_CHOICES[0][0])):
            street_address = self.cleaned_data['street_address']
            if street_address == '':
                raise forms.ValidationError(_('This field is required.'), code='required')
            return street_address
        

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
    name = forms.CharField(
            label=_("Full Name"),
            help_text="",
            required=True,
            widget=forms.TextInput(attrs={'class': 'form-control','placeholder':_("Full Name"),}))
    email = forms.EmailField(
            label=_("Email"),
            help_text="",
            required=True,
            widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':_("Email"),}))
    notes = forms.CharField(
            label=_("Notes"),
            help_text="",
            required=True,
            widget=forms.Textarea(attrs={'class': 'form-control','placeholder':_("Notes"),'rows':5}))
    permission = forms.BooleanField(required=True, label=_('Pursuant to art. 13 of Legislative Decree 30 June 2003 n. 196 we wish to inform you that the personal data supplied by you with the completion and submission of this form will be used only to respond to your request.'), widget=forms.CheckboxInput())
    captcha = CaptchaField(
            label=_("Control string"),
            help_text=_("Enter these 5 characters in the textbox on the right"),
            required=True,)

#180409 MMR
class ConfighomeForm(ModelForm):
    poi = forms.ModelChoiceField(Poi.objects.all(),
        required=False,
        label="Risorsa",
        widget=autocomplete.ModelSelect2(url='risorsa-ok-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli risorsa','style':'width:40%'})
        )
    poitype = forms.ModelChoiceField(Poitype.objects.all(),
        required=False,
        label="Categoria",
        widget=autocomplete.ModelSelect2(url='categoria-autocomplete',attrs={'data-minimum-input-length': 3, 'data-placeholder': 'Scegli risorsa','style':'width:40%'})
    )