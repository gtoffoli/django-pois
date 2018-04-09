# Generated by Django 2.0.1 on 2018-04-09 13:47

import autoslug.fields
from django.conf import settings
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Odonym',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(editable=True, populate_from='name', unique=True)),
                ('short', models.CharField(blank=True, max_length=120, null=True, verbose_name='In breve')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Descrizione')),
                ('web', models.TextField(blank=True, help_text='uno per riga', verbose_name='Siti web')),
                ('modified', models.DateTimeField(auto_now=True, null=True, verbose_name='Mod. il')),
            ],
            options={
                'verbose_name': 'toponimo',
                'verbose_name_plural': 'toponimi',
            },
        ),
        migrations.CreateModel(
            name='Poi',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nome')),
                ('code', models.CharField(blank=True, max_length=20, null=True, verbose_name='Codice')),
                ('short', models.CharField(blank=True, max_length=120, null=True, verbose_name='Descriz. breve')),
                ('description', models.TextField(blank=True, verbose_name='Descrizione')),
                ('othertags', models.CharField(blank=True, max_length=100, verbose_name='Altre keyword')),
                ('pro_com', models.IntegerField(blank=True, default=58091, null=True, verbose_name='Comune')),
                ('street_address', models.CharField(blank=True, max_length=100, verbose_name='Indirizzo')),
                ('housenumber', models.CharField(blank=True, max_length=16, verbose_name='Civico')),
                ('zipcode', models.CharField(blank=True, max_length=5, verbose_name='CAP')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='Latitudine')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='Longitudine')),
                ('point', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326, verbose_name='Posizione')),
                ('phone', models.TextField(blank=True, help_text='uno per riga', verbose_name='Numeri telefonici')),
                ('email', models.TextField(blank=True, help_text='uno per riga', verbose_name='Indirizzi email')),
                ('web', models.TextField(blank=True, help_text='uno per riga', verbose_name='Indirizzi web')),
                ('video', models.TextField(blank=True, help_text='uno per riga', verbose_name='Indirizzi video')),
                ('feeds', models.TextField(blank=True, help_text=' rss e atom, uno per riga', verbose_name='Indirizzi di feeds')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Note')),
                ('source', models.TextField(blank=True, verbose_name='Fonte')),
                ('contributor', models.CharField(blank=True, max_length=20, verbose_name='Contributo di')),
                ('creator', models.CharField(blank=True, max_length=20, verbose_name='Compilatore')),
                ('modified', models.DateField(auto_now=True, null=True, verbose_name='Mod. il')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='logos', verbose_name='Logo (immagine)')),
                ('slug', autoslug.fields.AutoSlugField(blank=True, editable=True, null=True, populate_from='name', unique=True)),
                ('kind', models.IntegerField(choices=[(0, 'servizio'), (1, 'struttura'), (2, 'consorzio'), (3, 'associazione di categoria')], default=1, null=True, verbose_name='Tipo')),
                ('partnership', models.IntegerField(choices=[(0, '-'), (1, 'socio'), (2, 'partner'), (3, 'sponsor')], default=0, null=True, verbose_name='Partnership')),
                ('state', models.IntegerField(choices=[(0, 'new'), (1, 'ok'), (2, 'off')], default=0, null=True, verbose_name='Stato')),
                ('careof', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poi_careof', to='pois.Poi', verbose_name='A cura di')),
                ('host', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poi_host', to='pois.Poi', verbose_name='Ospitato da')),
                ('lasteditor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poi_lasteditor', to=settings.AUTH_USER_MODEL, verbose_name='Mod. da')),
                ('members', models.ManyToManyField(related_name='poi_members', to=settings.AUTH_USER_MODEL, verbose_name='Membri')),
            ],
            options={
                'verbose_name': 'risorsa',
                'verbose_name_plural': 'risorse',
            },
        ),
        migrations.CreateModel(
            name='Poitype',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('klass', models.CharField(blank=True, max_length=10, null=True, unique=True)),
                ('name_en', models.CharField(blank=True, max_length=80)),
                ('name', models.CharField(blank=True, max_length=80)),
                ('icon', models.CharField(blank=True, max_length=20, null=True)),
                ('color', models.CharField(blank=True, max_length=20, null=True)),
                ('active', models.BooleanField(default=False)),
                ('slug', autoslug.fields.AutoSlugField(editable=True, populate_from='name', unique=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True, verbose_name='Mod. il')),
            ],
            options={
                'verbose_name': 'tipo di risorsa',
                'verbose_name_plural': 'tipi di risorsa',
                'ordering': ['klass'],
            },
        ),
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, max_length=10, null=True, verbose_name='Codice')),
                ('name', models.CharField(max_length=100, verbose_name='Nome')),
                ('slug', autoslug.fields.AutoSlugField(editable=True, populate_from='name', unique=True)),
                ('short', models.CharField(blank=True, max_length=200, null=True, verbose_name='In breve')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Descrizione')),
                ('web', models.TextField(blank=True, help_text='uno per riga', verbose_name='Siti web')),
                ('coords', models.TextField(blank=True, null=True, verbose_name='Coordinate')),
                ('geom', django.contrib.gis.db.models.fields.MultiLineStringField(blank=True, null=True, srid=4326, verbose_name='Geometria')),
                ('width', models.IntegerField(blank=True, default=200, null=True, verbose_name='Larghezza (m)')),
                ('modified', models.DateTimeField(auto_now=True, null=True, verbose_name='Mod. il')),
                ('state', models.IntegerField(choices=[(0, 'new'), (1, 'ok'), (2, 'off')], default=0, null=True, verbose_name='Stato')),
                ('pois', models.ManyToManyField(related_name='poi_route', to='pois.Poi')),
            ],
            options={
                'verbose_name': 'itinerario',
                'verbose_name_plural': 'itinerari',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Sourcetype',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=40)),
            ],
            options={
                'verbose_name': 'tipo di fonte',
                'verbose_name_plural': 'tipi di fonte',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_en', models.CharField(blank=True, max_length=40)),
                ('name', models.CharField(blank=True, max_length=40)),
                ('slug', autoslug.fields.AutoSlugField(editable=True, populate_from='name', unique=True)),
                ('weight', models.IntegerField(blank=True, default=1, null=True, verbose_name='Importanza')),
                ('color', models.CharField(blank=True, max_length=20, null=True, verbose_name='Colore')),
                ('modified', models.DateTimeField(auto_now=True, null=True, verbose_name='Mod. il')),
                ('tags', models.ManyToManyField(blank=True, related_name='_tag_tags_+', to='pois.Tag')),
            ],
            options={
                'verbose_name': 'tag',
                'verbose_name_plural': 'tags',
                'ordering': ('weight', 'name'),
            },
        ),
        migrations.CreateModel(
            name='TempZone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, verbose_name='Codice')),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=23032, verbose_name='Geometria')),
            ],
        ),
        migrations.CreateModel(
            name='Zone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, verbose_name='Codice')),
                ('name', models.CharField(max_length=50, verbose_name='Nome')),
                ('pro_com', models.IntegerField(blank=True, default=58091, null=True, verbose_name='Comune')),
                ('slug', autoslug.fields.AutoSlugField(editable=True, populate_from='name', unique=True)),
                ('short', models.CharField(blank=True, max_length=200, null=True, verbose_name='Toponimi')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Descrizione')),
                ('web', models.TextField(blank=True, help_text='uno per riga', verbose_name='Siti web')),
                ('shape_area', models.FloatField(blank=True, null=True, verbose_name='Area')),
                ('shape_len', models.FloatField(blank=True, null=True, verbose_name='Perimetro')),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=23032, verbose_name='Geometria')),
                ('modified', models.DateTimeField(auto_now=True, null=True, verbose_name='Mod. il')),
                ('careof', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='zone_careof', to='pois.Poi', verbose_name='A cura di')),
                ('pois', models.ManyToManyField(related_name='zone_pois', to='pois.Poi')),
                ('zones', models.ManyToManyField(blank=True, related_name='_zone_zones_+', to='pois.Zone', verbose_name='Vedi anche')),
            ],
            options={
                'verbose_name': 'zona',
                'verbose_name_plural': 'zone',
                'ordering': ['zonetype', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Zonetype',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_en', models.CharField(blank=True, max_length=40)),
                ('name', models.CharField(max_length=40)),
                ('name_plural_en', models.CharField(blank=True, max_length=40)),
                ('name_plural', models.CharField(blank=True, max_length=40)),
                ('slug', autoslug.fields.AutoSlugField(editable=True, populate_from='name', unique=True)),
            ],
            options={
                'verbose_name': 'tipo di zona',
                'verbose_name_plural': 'tipi di zona',
            },
        ),
        migrations.AddField(
            model_name='zone',
            name='zonetype',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='pois.Zonetype'),
        ),
        migrations.AddField(
            model_name='poitype',
            name='tags',
            field=models.ManyToManyField(blank=True, to='pois.Tag'),
        ),
        migrations.AddField(
            model_name='poi',
            name='moretypes',
            field=models.ManyToManyField(blank=True, related_name='poi_moretypes', to='pois.Poitype', verbose_name='Altre categorie'),
        ),
        migrations.AddField(
            model_name='poi',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poi_owner', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='poi',
            name='pois',
            field=models.ManyToManyField(to='pois.Poi', verbose_name='Risorse correlate'),
        ),
        migrations.AddField(
            model_name='poi',
            name='poitype',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='poi_poitype', to='pois.Poitype', to_field='klass', verbose_name='Categoria primaria'),
        ),
        migrations.AddField(
            model_name='poi',
            name='routes',
            field=models.ManyToManyField(blank=True, to='pois.Route', verbose_name='Route'),
        ),
        migrations.AddField(
            model_name='poi',
            name='sourcetype',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='pois.Sourcetype', verbose_name='Tipo di fonte'),
        ),
        migrations.AddField(
            model_name='poi',
            name='street',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='poi_street', to='pois.Odonym', verbose_name='Toponimo (es: Via Po)'),
        ),
        migrations.AddField(
            model_name='poi',
            name='tags',
            field=models.ManyToManyField(to='pois.Tag'),
        ),
        migrations.AddField(
            model_name='poi',
            name='zones',
            field=models.ManyToManyField(blank=True, to='pois.Zone', verbose_name='Zone'),
        ),
    ]
