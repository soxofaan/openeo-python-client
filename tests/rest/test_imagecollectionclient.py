import pytest

import openeo
from openeo.graphbuilder import GraphBuilder
from openeo.imagecollection import CollectionMetadata
from openeo.rest.imagecollectionclient import ImageCollectionClient

API_URL = "http://localhost:8000/api"


@pytest.fixture
def session040(requests_mock):
    session = openeo.connect(API_URL)
    requests_mock.get(API_URL + "/", json={"version": "0.4.0"})
    return session


@pytest.fixture
def sentinel2(session040, requests_mock):
    """Set up a connection with a SENTINEL2 image collection"""
    requests_mock.get(API_URL + "/collections/SENTINEL2", json={
        "properties": {
            "cube:dimensions": {
                "spectral": {
                    "type": "bands",
                    "values": ["B2", "B3", "B4", "B8"]
                }
            },
            "eo:bands": [
                {"name": "B2", "common_name": "blue", "center_wavelength": 0.4966},
                {"name": "B3", "common_name": "green", "center_wavelength": 0.560},
                {"name": "B4", "common_name": "red", "center_wavelength": 0.6645},
                {"name": "B8", "common_name": "nir", "center_wavelength": 0.8351}
            ]
        },
    })
    return session040


def test_metadata_from_api(session040, requests_mock):
    requests_mock.get(API_URL + "/collections/SENTINEL2", json={"foo": "bar"})
    metadata = session040.collection_metadata("SENTINEL2")
    assert metadata.get("foo") == "bar"


def test_metadata_load_collection(session040, requests_mock):
    requests_mock.get(API_URL + "/collections/SENTINEL2", json={
        "properties": {
            "cube:dimensions": {
                "bands": {"type": "bands", "values": ["B2", "B3"]}
            },
            "eo:bands": [
                {"name": "B2", "common_name": "blue"},
                {"name": "B3", "common_name": "green"},
            ]
        }
    })
    im = ImageCollectionClient.load_collection('SENTINEL2', session=session040)
    assert im.metadata.bands == [
        CollectionMetadata.Band("B2", "blue", None),
        CollectionMetadata.Band("B3", "green", None)
    ]


def test_empty_mask():
    from shapely import geometry
    polygon = geometry.Polygon([[1.0, 1.0], [2.0, 1.0], [2.0, 1.0], [1.0, 1.0]])

    client = ImageCollectionClient(node_id=None, builder=GraphBuilder(), session=None)

    with pytest.raises(ValueError, match=r"Mask .+ has an area of 0.0"):
        client.mask(polygon)


def test_metadata_bands_dimension(sentinel2):
    im = sentinel2.load_collection("SENTINEL2")
    assert im.metadata.bands_dimension == "spectral"


def test_bands_dimension_process_graph(sentinel2):
    im = sentinel2.load_collection("SENTINEL2")
    band = im.band("B3")
    reduce_node, = band.builder.get_by_process_id("reduce")
    assert reduce_node["arguments"]["dimension"] == "spectral"


def test_bands_dimension_process_graph_alt(session040, requests_mock):
    requests_mock.get(API_URL + "/collections/FOOBAR", json={
        "properties": {"cube:dimensions": {"zpektrul": {"type": "bands", "values": ["BAR", "BAZ"]}}},
    })
    im = session040.load_collection("FOOBAR")
    band = im.band("BAR")
    reduce_node, = band.builder.get_by_process_id("reduce")
    assert reduce_node["arguments"]["dimension"] == "zpektrul"


def test_bands_dimension_band_math(sentinel2):
    im = sentinel2.load_collection("SENTINEL2")
    b2 = im.band("B2")
    b3 = im.band("B3")
    b4 = im.band("B4")
    c23 = b2 + b3
    c234 = c23 + b4
