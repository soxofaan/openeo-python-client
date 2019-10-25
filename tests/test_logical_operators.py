from unittest import TestCase

import requests_mock
from mock import MagicMock

import openeo
from . import load_json_resource


@requests_mock.mock()
class TestLogicalOps(TestCase):

    def test_not_equal(self, m):
        # configuration phase: define username, endpoint, parameters?
        session = openeo.connect("http://localhost:8000/api")
        session.post = MagicMock()
        session.download = MagicMock()

        m.get("http://localhost:8000/api/", json={"version": "0.4.0"})
        m.get("http://localhost:8000/api/collections", json={"collections": [{"product_id": "sentinel2_subset"}]})
        m.get("http://localhost:8000/api/collections/SENTINEL2_SCF", json={
            "product_id": "sentinel2_subset",
            "properties": {
                "cube:dimensions": {
                    "layer": {"type": "bands", "values": ["SCENECLASSIFICATION"]}
                },
            },
        })

        # discovery phase: find available data
        # basically user needs to find available data on a website anyway?
        # like the imagecollection ID on: https://earthengine.google.com/datasets/

        # access multiband 4D (x/y/time/band) coverage
        s2_radio = session.imagecollection("SENTINEL2_SCF")

        scf_bands = s2_radio.band('SCENECLASSIFICATION')

        mask = scf_bands != 4

        mask.download("out.geotiff", format="GTIFF")

        session.download.assert_called_once()
        actual_graph = session.download.call_args_list[0][0][0]
        expected_graph = load_json_resource('data/notequal.json')
        assert actual_graph == expected_graph

    def test_or(self, m):
        session = openeo.connect("http://localhost:8000/api")
        session.post = MagicMock()
        session.download = MagicMock()

        m.get("http://localhost:8000/api/", json={"version": "0.4.0"})
        m.get("http://localhost:8000/api/collections", json={"collections": [{"product_id": "sentinel2_subset"}]})
        m.get("http://localhost:8000/api/collections/SENTINEL2_SCF", json={
            "product_id": "sentinel2_subset",
            "properties": {
                "cube:dimensions": {
                    "layer": {"type": "bands", "values": ["SCENECLASSIFICATION"]}
                },
            },
        })

        ic = session.imagecollection("SENTINEL2_SCF")
        data = ic.band('SCENECLASSIFICATION')
        # TODO: this expression (twice `data`) creates a duplicate `arrayelement` in the process graph
        mask = (data == 2) | (data == 5)

        mask.download("out.geotiff", format="GTIFF")
        session.download.assert_called_once()
        actual_graph = session.download.call_args_list[0][0][0]
        expected_graph = load_json_resource('data/logical_or.json')
        assert actual_graph == expected_graph

    def test_and(self, m):
        session = openeo.connect("http://localhost:8000/api")
        session.post = MagicMock()
        session.download = MagicMock()

        m.get("http://localhost:8000/api/", json={"version": "0.4.0"})
        m.get("http://localhost:8000/api/collections", json={"collections": [{"product_id": "sentinel2_subset"}]})
        m.get("http://localhost:8000/api/collections/SENTINEL2_SCF", json={
            "product_id": "sentinel2_subset",
            "properties": {
                "cube:dimensions": {
                    "spectral": {"type": "bands", "values": ["B1", "B2"]}
                },
            },
        })

        ic = session.imagecollection("SENTINEL2_SCF")
        b1 = ic.band('B1')
        b2 = ic.band('B2')
        mask = (b1 == 2) & (b2 == 5)

        mask.download("out.geotiff", format="GTIFF")
        session.download.assert_called_once()
        actual_graph = session.download.call_args_list[0][0][0]
        expected_graph = load_json_resource('data/logical_and.json')
        assert actual_graph == expected_graph
