from django.urls import path
from . import views

# Mounted under /api/dspace-config/cris-layout/

urlpatterns = [
    # Entity overview
    path("entities/",                       views.CrisLayoutEntityListView.as_view(),          name="cl-entity-list"),
    path("entities/<str:entity>/",          views.CrisLayoutEntityView.as_view(),              name="cl-entity-detail"),

    # Export (XLS download)
    path("export/",                         views.CrisLayoutExportView.as_view(),              name="cl-export"),

    # Tabs
    path("tabs/",                           views.CrisLayoutTabListView.as_view(),             name="cl-tab-list"),
    path("tabs/<int:pk>/",                  views.CrisLayoutTabDetailView.as_view(),           name="cl-tab-detail"),

    # Tab2Box mappings
    path("tab2box/",                        views.CrisLayoutTab2BoxListView.as_view(),         name="cl-tab2box-list"),
    path("tab2box/<int:pk>/",               views.CrisLayoutTab2BoxDetailView.as_view(),       name="cl-tab2box-detail"),

    # Boxes
    path("boxes/",                          views.CrisLayoutBoxListView.as_view(),             name="cl-box-list"),
    path("boxes/<int:pk>/",                 views.CrisLayoutBoxDetailView.as_view(),           name="cl-box-detail"),

    # Box→Metadata fields
    path("box-fields/",                     views.CrisLayoutBox2MetadataListView.as_view(),    name="cl-box-field-list"),
    path("box-fields/<int:pk>/",            views.CrisLayoutBox2MetadataDetailView.as_view(),  name="cl-box-field-detail"),

    # Metadata groups
    path("metadata-groups/",               views.CrisLayoutMetadataGroupListView.as_view(),   name="cl-metagroup-list"),
    path("metadata-groups/<int:pk>/",      views.CrisLayoutMetadataGroupDetailView.as_view(), name="cl-metagroup-detail"),
]
