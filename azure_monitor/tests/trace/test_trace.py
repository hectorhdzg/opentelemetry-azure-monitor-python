# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


import json
import os
import shutil
import unittest
from unittest import mock

# pylint: disable=import-error
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import Link, SpanContext, SpanKind
from opentelemetry.trace.status import Status, StatusCanonicalCode

from azure_monitor.export import ExportResult
from azure_monitor.export.trace import AzureMonitorSpanExporter
from azure_monitor.options import ExporterOptions

TEST_FOLDER = os.path.abspath(".test")
STORAGE_PATH = os.path.join(TEST_FOLDER)


# pylint: disable=invalid-name
def setUpModule():
    os.makedirs(TEST_FOLDER)


# pylint: disable=invalid-name
def tearDownModule():
    shutil.rmtree(TEST_FOLDER)


def throw(exc_type, *args, **kwargs):
    def func(*_args, **_kwargs):
        raise exc_type(*args, **kwargs)

    return func


# pylint: disable=import-error
# pylint: disable=protected-access
# pylint: disable=too-many-lines
class TestAzureExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.clear()
        os.environ[
            "APPINSIGHTS_INSTRUMENTATIONKEY"
        ] = "1234abcd-5678-4efa-8abc-1234567890ab"
        cls._exporter = AzureMonitorSpanExporter(storage_path=STORAGE_PATH)

    def setUp(self):
        for filename in os.listdir(STORAGE_PATH):
            file_path = os.path.join(STORAGE_PATH, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except OSError as e:
                print("Failed to delete %s. Reason: %s" % (file_path, e))

    def test_constructor(self):
        """Test the constructor."""
        exporter = AzureMonitorSpanExporter(
            instrumentation_key="4321abcd-5678-4efa-8abc-1234567890ab",
            storage_path=os.path.join(TEST_FOLDER, self.id()),
        )
        self.assertIsInstance(exporter.options, ExporterOptions)
        self.assertEqual(
            exporter.options.instrumentation_key,
            "4321abcd-5678-4efa-8abc-1234567890ab",
        )
        self.assertEqual(
            exporter.options.storage_path, os.path.join(TEST_FOLDER, self.id())
        )

    def test_export_empty(self):
        exporter = self._exporter
        exporter.export([])
        self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    def test_export_failure(self):
        exporter = self._exporter
        with mock.patch(
            "azure_monitor.export.trace.AzureMonitorSpanExporter._transmit"
        ) as transmit:  # noqa: E501
            test_span = Span(
                name="test",
                context=SpanContext(
                    trace_id=36873507687745823477771305566750195431,
                    span_id=12030755672171557338,
                    is_remote=False,
                ),
            )
            test_span.start()
            test_span.end()
            transmit.return_value = ExportResult.FAILED_RETRYABLE
            exporter.export([test_span])
        self.assertEqual(len(os.listdir(exporter.storage.path)), 1)
        self.assertIsNone(exporter.storage.get())

    def test_export_success(self):
        exporter = self._exporter
        test_span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557338,
                is_remote=False,
            ),
        )
        test_span.start()
        test_span.end()
        with mock.patch(
            "azure_monitor.export.trace.AzureMonitorSpanExporter._transmit"
        ) as transmit:  # noqa: E501
            transmit.return_value = ExportResult.SUCCESS
            storage_mock = mock.Mock()
            exporter._transmit_from_storage = storage_mock
            exporter.export([test_span])
            self.assertEqual(storage_mock.call_count, 1)
            self.assertEqual(len(os.listdir(exporter.storage.path)), 0)

    @mock.patch("azure_monitor.export.trace.logger")
    def test_export_exception(self, logger_mock):
        test_span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557338,
                is_remote=False,
            ),
        )
        test_span.start()
        test_span.end()
        exporter = self._exporter
        with mock.patch(
            "azure_monitor.export.trace.AzureMonitorSpanExporter._transmit",
            throw(Exception),
        ):  # noqa: E501
            result = exporter.export([test_span])
            self.assertEqual(result, SpanExportResult.FAILURE)
            self.assertEqual(logger_mock.exception.called, True)

    def test_export_not_retryable(self):
        exporter = self._exporter
        test_span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557338,
                is_remote=False,
            ),
        )
        test_span.start()
        test_span.end()
        with mock.patch(
            "azure_monitor.export.trace.AzureMonitorSpanExporter._transmit"
        ) as transmit:  # noqa: E501
            transmit.return_value = ExportResult.FAILED_NOT_RETRYABLE
            result = exporter.export([test_span])
            self.assertEqual(result, SpanExportResult.FAILURE)

    def test_span_to_envelope_none(self):
        exporter = self._exporter
        self.assertIsNone(exporter._span_to_envelope(None))

    # pylint: disable=too-many-statements
    def test_span_to_envelope(self):
        exporter = AzureMonitorSpanExporter(
            instrumentation_key="12345678-1234-5678-abcd-12345678abcd",
            storage_path=os.path.join(TEST_FOLDER, self.id()),
        )

        parent_span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557338,
                is_remote=False,
            ),
        )

        start_time = 1575494316027613500
        end_time = start_time + 1001000000

        # SpanKind.CLIENT HTTP
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "GET//wiki/Rabbit")
        self.assertEqual(
            envelope.data.base_data.data,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_data.target, "www.wikipedia.org")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.result_code, "200")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.type, "HTTP")
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # SpanKind.CLIENT unknown type
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={},
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "test")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.type, None)
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # SpanKind.CLIENT missing method
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "test")
        self.assertEqual(
            envelope.data.base_data.data,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_data.target, "www.wikipedia.org")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.result_code, "200")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.type, "HTTP")
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # SpanKind.SERVER HTTP - 200 request
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.path": "/wiki/Rabbit",
                "http.route": "/wiki/Rabbit",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.Request"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(
            envelope.tags["ai.operation.name"], "GET /wiki/Rabbit"
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.response_code, "200")
        self.assertEqual(envelope.data.base_data.name, "GET /wiki/Rabbit")
        self.assertEqual(envelope.data.base_data.success, True)
        self.assertEqual(
            envelope.data.base_data.url,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_type, "RequestData")

        # SpanKind.SERVER HTTP - Failed request
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.path": "/wiki/Rabbit",
                "http.route": "/wiki/Rabbit",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.Request"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(
            envelope.tags["ai.operation.name"], "GET /wiki/Rabbit"
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.response_code, "400")
        self.assertEqual(envelope.data.base_data.name, "GET /wiki/Rabbit")
        self.assertEqual(envelope.data.base_data.success, False)
        self.assertEqual(
            envelope.data.base_data.url,
            "https://www.wikipedia.org/wiki/Rabbit",
        )
        self.assertEqual(envelope.data.base_type, "RequestData")

        # SpanKind.SERVER unknown type
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.path": "/wiki/Rabbit",
                "http.route": "/wiki/Rabbit",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.Request"
        )
        self.assertEqual(
            envelope.tags["ai.operation.parentId"], "a6f5d48acb4d31da"
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_type, "RequestData")

        # SpanKind.INTERNAL
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=None,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={"key1": "value1"},
            events=None,
            links=[],
            kind=SpanKind.INTERNAL,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.ikey, "12345678-1234-5678-abcd-12345678abcd")
        self.assertEqual(
            envelope.name, "Microsoft.ApplicationInsights.RemoteDependency"
        )
        self.assertRaises(
            KeyError, lambda: envelope.tags["ai.operation.parentId"]
        )
        self.assertEqual(
            envelope.tags["ai.operation.id"],
            "1bbd944a73a05d89eab5d3740a213ee7",
        )
        self.assertEqual(envelope.time, "2019-12-04T21:18:36.027613Z")
        self.assertEqual(envelope.data.base_data.name, "test")
        self.assertEqual(envelope.data.base_data.duration, "0.00:00:01.001")
        self.assertEqual(envelope.data.base_data.id, "a6f5d48acb4d31d9")
        self.assertEqual(envelope.data.base_data.type, "InProc")
        self.assertEqual(envelope.data.base_type, "RemoteDependencyData")

        # Attributes
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
                "test": "asd",
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(len(envelope.data.base_data.properties), 2)
        self.assertEqual(
            envelope.data.base_data.properties["component"], "http"
        )
        self.assertEqual(envelope.data.base_data.properties["test"], "asd")

        # Links
        links = []
        links.append(
            Link(
                context=SpanContext(
                    trace_id=36873507687745823477771305566750195432,
                    span_id=12030755672171557338,
                    is_remote=False,
                )
            )
        )
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 200,
            },
            events=None,
            links=links,
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(len(envelope.data.base_data.properties), 2)
        json_dict = json.loads(
            envelope.data.base_data.properties["_MS.links"]
        )[0]
        self.assertEqual(json_dict["id"], "a6f5d48acb4d31da")

        # Status
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 500,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.response_code, "500")
        self.assertFalse(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 500,
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.result_code, "500")
        self.assertFalse(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.response_code, "0")
        self.assertTrue(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.result_code, "0")
        self.assertTrue(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.UNKNOWN)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.response_code, "2")
        self.assertFalse(envelope.data.base_data.success)

        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
            },
            events=None,
            links=[],
            kind=SpanKind.CLIENT,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.UNKNOWN)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.result_code, "2")
        self.assertFalse(envelope.data.base_data.success)

        # Server route attribute
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.route": "/wiki/Rabbit",
                "http.path": "/wiki/Rabbitz",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(
            envelope.data.base_data.properties["request.name"],
            "GET /wiki/Rabbit",
        )
        self.assertEqual(
            envelope.data.base_data.properties["request.url"],
            "https://www.wikipedia.org/wiki/Rabbit",
        )

        # Server method attribute missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.path": "/wiki/Rabbitz",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter._span_to_envelope(span)
        self.assertIsNone(envelope.data.base_data.name)

        # Server route attribute missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.path": "/wiki/Rabbitz",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter._span_to_envelope(span)
        self.assertEqual(envelope.data.base_data.name, "GET")
        self.assertEqual(
            envelope.data.base_data.properties["request.name"],
            "GET /wiki/Rabbitz",
        )
        self.assertEqual(
            envelope.data.base_data.properties["request.url"],
            "https://www.wikipedia.org/wiki/Rabbit",
        )

        # Server route and path attribute missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.url": "https://www.wikipedia.org/wiki/Rabbit",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter._span_to_envelope(span)
        self.assertIsNone(
            envelope.data.base_data.properties.get("request.name")
        )
        self.assertEqual(
            envelope.data.base_data.properties["request.url"],
            "https://www.wikipedia.org/wiki/Rabbit",
        )

        # Server http.url missing
        span = Span(
            name="test",
            context=SpanContext(
                trace_id=36873507687745823477771305566750195431,
                span_id=12030755672171557337,
                is_remote=False,
            ),
            parent=parent_span,
            sampler=None,
            trace_config=None,
            resource=None,
            attributes={
                "component": "HTTP",
                "http.method": "GET",
                "http.route": "/wiki/Rabbit",
                "http.path": "/wiki/Rabbitz",
                "http.status_code": 400,
            },
            events=None,
            links=[],
            kind=SpanKind.SERVER,
        )
        span.start(start_time=start_time)
        span.end(end_time=end_time)
        span.status = Status(canonical_code=StatusCanonicalCode.OK)
        envelope = exporter._span_to_envelope(span)
        self.assertIsNone(envelope.data.base_data.url)
        self.assertIsNone(
            envelope.data.base_data.properties.get("request.url")
        )
