"""Bounded selection from an already connected MCP transport."""

import json
import re


NAME = re.compile(r'[A-Za-z0-9_.-]{1,128}\Z')


class CatalogUnavailable(ValueError):
    pass


def bounded_schema(schema):
    """Keep constraints and strip executable-looking prose and external schema links."""
    if isinstance(schema, list):
        return [bounded_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    cleaned = {}
    for key, value in schema.items():
        if key in {'description', 'title', 'examples', 'default', '$comment', '$id', '$schema'}:
            continue
        if key in {'$ref', '$dynamicRef', '$recursiveRef'} and (not isinstance(value, str) or not value.startswith('#')):
            raise CatalogUnavailable('external MCP schema references are unsupported')
        if key in {'properties', 'patternProperties', '$defs', 'definitions'} and isinstance(value, dict):
            cleaned[key] = {name: bounded_schema(subschema) for name, subschema in value.items()}
        else:
            cleaned[key] = bounded_schema(value)
    return cleaned


class McpCatalog:
    """Cache one session's tool descriptors and expose only the authorized choice.

    The host supplies a connected request function after MCP initialization.
    This layer does not open a transport or call any discovered tool.
    """

    def __init__(self, request):
        self.request = request
        self.tools = None

    def invalidate(self, method):
        if method in {'notifications/tools/list_changed', 'transport/disconnected'}:
            self.tools = None

    def _get_tools(self):
        if self.tools is not None:
            return self.tools
        gathered, seen, params = {}, set(), {}
        for _ in range(8):
            page = self.request('tools/list', params)
            if not isinstance(page, dict) or not isinstance(page.get('tools'), list):
                raise CatalogUnavailable('invalid MCP tool list')
            for tool in page['tools']:
                if not isinstance(tool, dict) or not isinstance(tool.get('name'), str) or not NAME.fullmatch(tool['name']):
                    raise CatalogUnavailable('invalid MCP tool name')
                if tool['name'] in gathered or len(gathered) >= 128:
                    raise CatalogUnavailable('duplicate tool or catalog limit reached')
                schema = tool.get('inputSchema')
                if not isinstance(schema, dict) or schema.get('type') != 'object':
                    raise CatalogUnavailable('invalid MCP tool schema')
                if len(json.dumps(schema, ensure_ascii=False).encode('utf-8')) > 32768:
                    raise CatalogUnavailable('MCP tool schema exceeds the local limit')
                gathered[tool['name']] = schema
            cursor = page.get('nextCursor')
            if cursor is None:
                self.tools = gathered
                return gathered
            if not isinstance(cursor, str) or not cursor or len(cursor) > 1024 or cursor in seen:
                raise CatalogUnavailable('invalid MCP catalog cursor')
            seen.add(cursor)
            params = {'cursor': cursor}
        raise CatalogUnavailable('MCP catalog exceeded eight pages')

    def choose(self, capability, allowed, *, authorized=False, native=None):
        """Return a plan only. `allowed` is a local capability-to-tool map."""
        if not authorized:
            return {'state': 'permission_restricted', 'fallback': native}
        name = allowed.get(capability)
        if not name:
            return {'state': 'not_configured', 'fallback': native}
        try:
            schema = self._get_tools().get(name)
        except (CatalogUnavailable, TimeoutError, OSError, ValueError, TypeError, RecursionError):
            return {'state': 'discovery_failed', 'fallback': native}
        if schema is None:
            return {'state': 'unavailable', 'fallback': native}
        # Descriptions and server annotations never authorize tools or broaden scope.
        try:
            return {'state': 'available', 'tool': name, 'input_schema': bounded_schema(schema)}
        except (CatalogUnavailable, RecursionError):
            return {'state': 'unsupported_schema', 'fallback': native}
