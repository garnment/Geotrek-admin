import logging
from django.conf import settings
from django.http import Http404
from mapentity.views import (MapEntityCreate, MapEntityUpdate, MapEntityLayer, MapEntityList, MapEntityDetail,
                             MapEntityDelete, MapEntityViewSet, MapEntityFormat)
from rest_framework import permissions as rest_permissions, viewsets
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from geotrek.authent.decorators import same_structure_required

from geotrek.trekking.models import Trek
from .filters import SensitiveAreaFilterSet
from .forms import SensitiveAreaForm, RegulatorySensitiveAreaForm
from .models import SensitiveArea, Species
from .serializers import SensitiveAreaSerializer


logger = logging.getLogger(__name__)


class SensitiveAreaLayer(MapEntityLayer):
    queryset = SensitiveArea.objects.existing()
    properties = ['species', 'published']


class SensitiveAreaList(MapEntityList):
    queryset = SensitiveArea.objects.existing()
    filterform = SensitiveAreaFilterSet
    columns = ['id', 'species']


class SensitiveAreaFormatList(MapEntityFormat, SensitiveAreaList):
    columns = [
        'id', 'species',
    ]


class SensitiveAreaDetail(MapEntityDetail):
    queryset = SensitiveArea.objects.existing()

    def get_context_data(self, *args, **kwargs):
        context = super(SensitiveAreaDetail, self).get_context_data(*args, **kwargs)
        context['can_edit'] = self.get_object().same_structure(self.request.user)
        return context


class SensitiveAreaCreate(MapEntityCreate):
    model = SensitiveArea

    def get_form_class(self):
        if self.request.GET.get('category') == str(Species.REGULATORY):
            return RegulatorySensitiveAreaForm
        return SensitiveAreaForm


class SensitiveAreaUpdate(MapEntityUpdate):
    queryset = SensitiveArea.objects.existing()

    def get_form_class(self):
        if self.object.species.category == Species.REGULATORY:
            return RegulatorySensitiveAreaForm
        return SensitiveAreaForm

    @same_structure_required('sensitivity:sensitivearea_detail')
    def dispatch(self, *args, **kwargs):
        return super(SensitiveAreaUpdate, self).dispatch(*args, **kwargs)


class SensitiveAreaDelete(MapEntityDelete):
    model = SensitiveArea

    @same_structure_required('sensitivity:sensitivearea_detail')
    def dispatch(self, *args, **kwargs):
        return super(SensitiveAreaDelete, self).dispatch(*args, **kwargs)


class SensitiveAreaViewSet(MapEntityViewSet):
    model = SensitiveArea
    serializer_class = SensitiveAreaSerializer
    permission_classes = [rest_permissions.DjangoModelPermissionsOrAnonReadOnly]

    def get_queryset(self):
        qs = SensitiveArea.objects.existing()
        qs = qs.filter(published=True)

        if 'practices' in self.request.GET:
            qs = qs.filter(species__practices__name__in=self.request.GET['practices'].split(','))

        qs = qs.transform(settings.API_SRID, field_name='geom')
        return qs


class TrekSensitiveAreaViewSet(viewsets.ModelViewSet):
    model = SensitiveArea
    permission_classes = [rest_permissions.DjangoModelPermissionsOrAnonReadOnly]

    def get_serializer_class(self):
        class Serializer(SensitiveAreaSerializer, GeoFeatureModelSerializer):
            pass
        return Serializer

    def get_queryset(self):
        pk = self.kwargs['pk']
        try:
            trek = Trek.objects.existing().get(pk=pk)
        except Trek.DoesNotExist:
            raise Http404
        if not trek.is_public:
            raise Http404
        return trek.sensitive_areas.filter(published=True).transform(settings.API_SRID, field_name='geom')