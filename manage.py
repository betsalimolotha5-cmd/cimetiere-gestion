#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Configuration GDAL et GEOS pour Windows (AVANT d'importer Django)
os.environ['GDAL_LIBRARY_PATH'] = r'C:\Users\Mr WILSON\AppData\Local\Programs\OSGeo4W\bin\gdal313.dll'
os.environ['GEOS_LIBRARY_PATH'] = r'C:\Users\Mr WILSON\AppData\Local\Programs\OSGeo4W\bin\geos_c.dll'
os.environ['PATH'] = r'C:\Users\Mr WILSON\AppData\Local\Programs\OSGeo4W\bin;' + os.environ['PATH']


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()