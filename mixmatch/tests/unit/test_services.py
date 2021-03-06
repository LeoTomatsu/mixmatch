#   Copyright 2016 Massachusetts Open Cloud
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import json
from six.moves.urllib import parse
from testtools import testcase

from oslo_config import fixture as config_fixture

from mixmatch import services
from mixmatch.config import CONF
from mixmatch.tests.unit import samples


class Response(object):
    def __init__(self, text):
        self.text = text


# Source: http://stackoverflow.com/a/9468284
class Url(object):
    """Url object that can be compared with other url objects

    This comparison is done without regard to the vagaries of encoding,
    escaping, and ordering of parameters in query strings.
    """

    def __init__(self, url):
        parts = parse.urlparse(url)
        _query = frozenset(parse.parse_qsl(parts.query))
        _path = parse.unquote_plus(parts.path)
        parts = parts._replace(query=_query, path=_path)
        self.parts = parts

    def __eq__(self, other):
        return self.parts == other.parts

    def __hash__(self):
        return hash(self.parts)


VOLUMES = {
    'default': Response(json.dumps(
        samples.multiple_sps['/volume/v2/id/volumes/detail'][0]
    )),
    'sp1': Response(json.dumps(
        samples.multiple_sps['/volume/v2/id/volumes/detail'][1]
    ))
}

VOLUMES_V1 = {
    'default': Response(json.dumps(
        samples.single_sp['/volume/v1/id/volumes/detail']
    )),
    'sp1': Response(json.dumps(
        samples.single_sp['/volume/v1/id/volumes/detail']
    ))
}

IMAGES = {
    'default': Response(json.dumps(
        samples.multiple_sps['/image/v2/images'][0]
    )),
    'sp1': Response(json.dumps(
        samples.multiple_sps['/image/v2/images'][1]
    ))
}

SMALLEST_IMAGE = min(
    samples.single_sp['/image/v2/images']['images'],
    key=lambda d: d['size']
)['id']
EARLIEST_IMAGE = min(
    samples.single_sp['/image/v2/images']['images'],
    key=lambda d: d['updated_at']
)['id']
SECOND_EARLIEST_IMAGE = sorted(
    samples.single_sp['/image/v2/images']['images'],
    key=lambda d: d['updated_at']
)[1]['id']
LATEST_IMAGE = sorted(
    samples.single_sp['/image/v2/images']['images'],
    key=lambda d: d['updated_at']
)[-1]['id']

IMAGE_PATH = 'http://localhost/image/images'
VOLUME_PATH = 'http://localhost/volume/volumes'

IMAGES_IN_SAMPLE = 3
VOLUMES_IN_SAMPLE = 3

API_VERSIONS = 'v3.2, v2.0, v1'
NUM_OF_VERSIONS = 3
IMAGE_UNVERSIONED = 'http://localhost/image'
IMAGE_VERSIONED = 'http://localhost/image/v3/'
VOLUME_UNVERSIONED = 'http://localhost/volume'
VOLUME_VERSIONED = 'http://localhost/volume/v3/'


class TestServices(testcase.TestCase):
    def setUp(self):
        super(TestServices, self).setUp()
        self.config_fixture = self.useFixture(config_fixture.Config(conf=CONF))

    def test_aggregate_key(self):
        # Aggregate 'images'
        response = json.loads(services.aggregate(IMAGES, 'images', 'image'))
        self.assertEqual(IMAGES_IN_SAMPLE, len(response['images']))

        # Aggregate 'volumes'
        response = json.loads(services.aggregate(VOLUMES, 'volumes', 'volume'))
        self.assertEqual(VOLUMES_IN_SAMPLE, len(response['volumes']))

    def test_aggregate_limit(self):
        params = {
            'limit': 1
        }
        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))
        self.assertEqual(1, len(response['images']))

        response = json.loads(services.aggregate(VOLUMES, 'volumes', 'volume',
                                                 params=params,
                                                 path=IMAGE_PATH))
        self.assertEqual(1, len(response['volumes']))

    def test_aggregate_sort_images_ascending(self):
        """Sort images by smallest size, ascending."""
        params = {
            'sort': 'size:asc'
        }
        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))
        self.assertEqual(response['images'][0]['id'], SMALLEST_IMAGE)

    def test_aggregate_sort_images_limit(self):
        """Sort images by smallest size, ascending, limit to 1, alt format."""
        params = {
            'sort_key': 'size',
            'sort_dir': 'asc',
            'limit': 1
        }
        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))

        # Ensure the smallest is first and there is only 1 entry.
        self.assertEqual(response['images'][0]['id'], SMALLEST_IMAGE)
        self.assertEqual(1, len(response['images']))

        # Ensure the 'next' url is correct.
        self.assertEqual(
            Url(response['next']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params, marker=SMALLEST_IMAGE)
            ))
        )

    def test_sort_images_date_limit_ascending(self):
        """Sort images by last update, ascending, limit to 2."""
        params = {
            'sort': 'updated_at:asc',
            'limit': 2
        }
        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))

        # Check the first and second are the correct ids.
        self.assertEqual(response['images'][0]['id'], EARLIEST_IMAGE)
        self.assertEqual(response['images'][1]['id'], SECOND_EARLIEST_IMAGE)
        self.assertEqual(2, len(response['images']))

        # Check the next link
        self.assertEqual(
            Url(response['next']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params, marker=SECOND_EARLIEST_IMAGE)
            ))
        )

    def test_sort_images_date_limit_descending(self):
        """Sort images by last update, descending, limit 1."""
        params = {
            'sort': 'updated_at:desc',
            'limit': 1
        }
        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))

        # Check the id and size
        self.assertEqual(response['images'][0]['id'], LATEST_IMAGE)
        self.assertEqual(1, len(response['images']))

        # Check the next link
        self.assertEqual(
            Url(response['next']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params, marker=LATEST_IMAGE)
            ))
        )

    def test_sort_images_date_ascending_pagination(self):
        """Sort images by last update, ascending, skip the first one."""
        params = {
            'sort': 'updated_at:asc',
            'limit': 1,
            'marker': EARLIEST_IMAGE
        }
        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))

        # Ensure we skipped the first one
        self.assertEqual(response['images'][0]['id'], SECOND_EARLIEST_IMAGE)
        self.assertEqual(1, len(response['images']))

        # Next link
        self.assertEqual(
            Url(response['next']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params, marker=SECOND_EARLIEST_IMAGE)
            ))
        )

        # Start link
        self.assertEqual(
            Url(response['start']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params)
            ))
        )

    def test_marker_without_limit(self):
        """Test marker without limit."""
        params = {
            'sort': 'updated_at:asc',
            'marker': EARLIEST_IMAGE
        }

        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))

        # Ensure we skipped the first one
        self.assertEqual(response['images'][0]['id'], SECOND_EARLIEST_IMAGE)
        self.assertEqual(IMAGES_IN_SAMPLE - 1, len(response['images']))

        # Start link
        self.assertEqual(
            Url(response['start']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params)
            ))
        )

    def test_marker_last(self):
        """Test marker without limit, nothing to return."""
        params = {
            'sort': 'updated_at:asc',
            'marker': LATEST_IMAGE
        }

        response = json.loads(services.aggregate(IMAGES, 'images', 'image',
                                                 params=params,
                                                 path=IMAGE_PATH))

        # Ensure we skipped the first one
        self.assertEqual(0, len(response['images']))

        # Start link
        self.assertEqual(
            Url(response['start']),
            Url(self._prepare_url(
                IMAGE_PATH,
                self._prepare_params(params)
            ))
        )

    def test_list_api_versions(self):

        self.config_fixture.load_raw_values(image_api_versions=API_VERSIONS,
                                            volume_api_versions=API_VERSIONS)

        # List image api
        response = json.loads(services.list_api_versions('image',
                                                         IMAGE_UNVERSIONED))
        current_version = response['versions'][0]['id']
        current_version_status = response['versions'][0]['status']
        current_version_url = response['versions'][0]['links'][0]['href']

        self.assertEqual(NUM_OF_VERSIONS, len(response['versions']))
        self.assertEqual(current_version, 'v3.2')
        self.assertEqual(current_version_status, 'CURRENT')
        self.assertEqual(
            Url(current_version_url),
            Url(IMAGE_VERSIONED))

        # List volume api
        response = json.loads(services.list_api_versions('volume',
                                                         VOLUME_UNVERSIONED))
        current_version = response['versions'][0]['id']
        current_version_status = response['versions'][0]['status']
        current_version_url = response['versions'][0]['links'][1]['href']

        self.assertEqual(NUM_OF_VERSIONS, len(response['versions']))
        self.assertEqual(current_version, 'v3.2')
        self.assertEqual(current_version_status, 'CURRENT')
        self.assertEqual(
            Url(current_version_url),
            Url(VOLUME_VERSIONED))

    def test_remove_details_v2(self):
        """Test aggregation on volumes v2 with strip_details = True"""
        response = json.loads(services.aggregate(
            VOLUMES, 'volumes', 'volume', version='v2', strip_details=True
        ))
        for v in response['volumes']:
            self.assertEqual(
                set(v.keys()),
                {'id', 'links', 'name'}
            )

    def test_remove_details_v1(self):
        """Test aggregation on volumes v2 with strip_details = True"""
        response = json.loads(
            services.aggregate(VOLUMES_V1, 'volumes', 'volume',
                               version='v1', strip_details=True)
        )
        for v in response['volumes']:
            self.assertEqual(
                set(v.keys()),
                {'status', 'attachments', 'availability_zone',
                 'encrypted', 'source_volid', 'display_description',
                 'snapshot_id', 'id', 'size', 'display_name',
                 'bootable', 'created_at', 'multiattach',
                 'volume_type', 'metadata'}
            )

    @staticmethod
    def _prepare_params(user_params, marker=None):
        params = user_params.copy()
        if marker:
            params['marker'] = marker
        else:
            params.pop('marker', None)
        return params

    @staticmethod
    def _prepare_url(url, params):
        return '%s?%s' % (url, parse.urlencode(params))
