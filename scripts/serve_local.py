#!/usr/bin/env python3
"""
Local development server for testing visualizations.

Exports database to JSON and serves landing page with API endpoints.
Usage: python scripts/serve_local.py [--db PATH] [--port PORT]
"""
import argparse
import datetime
import http.server
import json
import os
import pathlib
import shutil
import socketserver
import sys
import tempfile
import threading
import webbrowser

# Add project root to path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.models
import src.export


class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves landing page and API data."""

    def __init__(self, *args, api_dir=None, landing_dir=None, **kwargs):
        self.api_dir = api_dir
        self.landing_dir = landing_dir
        super().__init__(*args, directory=landing_dir, **kwargs)

    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Serve API endpoints from exported JSON
        if self.path.startswith('/api/v1/'):
            api_path = self.path[8:]  # Remove '/api/v1/'

            # Remove query parameters if any
            if '?' in api_path:
                api_path = api_path.split('?')[0]

            # Map to file system
            if api_path == '' or api_path == '/':
                file_path = self.api_dir / 'index.json'
            elif api_path.startswith('terms/'):
                # /api/v1/terms/202530/ -> terms/202530.json
                term_code = api_path.split('/')[1]
                file_path = self.api_dir / 'terms' / f'{term_code}.json'
            elif api_path.startswith('search/'):
                # /api/v1/search/instructors.json
                search_file = api_path.split('/')[1]
                file_path = self.api_dir / 'search' / search_file
            else:
                file_path = self.api_dir / api_path

            if file_path.exists():
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Not found',
                    'path': str(file_path)
                }).encode())
                return

        # Serve landing page assets
        super().do_GET()

    def log_message(self, format, *args):
        # Customize log format
        if self.path.startswith('/api/'):
            print(f"[API] {args[0]} - {args[1]}")
        else:
            print(f"[WEB] {args[0]} - {args[1]}")


def export_database_to_api(db_path: str, output_dir: pathlib.Path):
    """Export database to API JSON structure."""
    print(f"\n📊 Exporting database: {db_path}")

    # Initialize database
    src.models.db.init(db_path)
    src.models.db.connect()

    # Create API directory structure
    api_dir = output_dir / 'api' / 'v1'
    terms_dir = api_dir / 'terms'
    search_dir = api_dir / 'search'

    api_dir.mkdir(parents=True, exist_ok=True)
    terms_dir.mkdir(parents=True, exist_ok=True)
    search_dir.mkdir(parents=True, exist_ok=True)

    # Get all terms
    terms = src.models.Term.select().order_by(src.models.Term.code.desc())

    if terms.count() == 0:
        print("⚠️  No terms found in database!")
        return api_dir

    print(f"   Found {terms.count()} terms")

    # Export each term
    term_index = []
    all_instructors = {}
    all_departments = {}
    total_courses = 0

    for term in terms:
        print(f"   Exporting {term.name} ({term.code})...")

        # Export term data
        term_data = src.export.export_term_to_dict(term.code)

        # Write term JSON
        term_file = terms_dir / f'{term.code}.json'
        with open(term_file, 'w') as f:
            json.dump(term_data, f, indent=2)

        # Count courses
        course_count = len(term_data['courses'])
        total_courses += course_count

        # Add to index
        term_index.append({
            'code': term.code,
            'name': term.name,
            'start_date': term.start_date.isoformat() if term.start_date else None,
            'end_date': term.end_date.isoformat() if term.end_date else None,
            'course_count': course_count,
        })

        # Collect instructor and department data for search
        for course in term_data['courses']:
            # Instructors
            for instructor in course['instructors']:
                if instructor not in all_instructors:
                    all_instructors[instructor] = []
                all_instructors[instructor].append({
                    'code': course['code'],
                    'title': course['title'],
                    'term': term.code
                })

            # Departments
            dept = course['code'].split()[0] if ' ' in course['code'] else course['code'].split('-')[0]
            if dept not in all_departments:
                all_departments[dept] = []
            all_departments[dept].append({
                'code': course['code'],
                'title': course['title'],
                'term': term.code
            })

    # Count instructors
    total_instructors = src.models.Instructor.select().count()

    # Write master index
    index_data = {
        'generated_at': datetime.datetime.now().isoformat(),
        'total_terms': len(term_index),
        'total_courses': total_courses,
        'total_instructors': total_instructors,
        'terms': term_index,
    }

    with open(api_dir / 'index.json', 'w') as f:
        json.dump(index_data, f, indent=2)

    # Write search indexes
    with open(search_dir / 'instructors.json', 'w') as f:
        json.dump({
            'generated_at': datetime.datetime.now().isoformat(),
            'instructors': all_instructors
        }, f, indent=2)

    with open(search_dir / 'departments.json', 'w') as f:
        json.dump({
            'generated_at': datetime.datetime.now().isoformat(),
            'departments': all_departments
        }, f, indent=2)

    print(f"✅ Export complete!")
    print(f"   📁 API directory: {api_dir}")
    print(f"   📊 {len(term_index)} terms, {total_courses} courses, {total_instructors} instructors")

    return api_dir


def serve(port: int, landing_dir: pathlib.Path, api_dir: pathlib.Path):
    """Start local development server."""

    # Create custom handler with our directories
    def handler_factory(*args, **kwargs):
        return DevServerHandler(*args, api_dir=api_dir, landing_dir=landing_dir, **kwargs)

    # Start server
    with socketserver.TCPServer(("", port), handler_factory) as httpd:
        url = f"http://localhost:{port}"
        print(f"\n🚀 Development server running at {url}")
        print(f"   📁 Serving from: {landing_dir}")
        print(f"   🔌 API data from: {api_dir}")
        print(f"\n   Press Ctrl+C to stop\n")

        # Auto-open browser after a short delay
        def open_browser():
            import time
            time.sleep(1)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")


def main():
    parser = argparse.ArgumentParser(
        description='Local development server for Penn Path Scraper visualizations'
    )
    parser.add_argument(
        '--db',
        default='courses.db',
        help='Path to database file (default: courses.db)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to serve on (default: 8000)'
    )
    parser.add_argument(
        '--no-export',
        action='store_true',
        help='Skip database export (use existing API files)'
    )
    parser.add_argument(
        '--output-dir',
        type=pathlib.Path,
        help='Output directory for API files (default: temp directory)'
    )

    args = parser.parse_args()

    # Paths
    db_path = pathlib.Path(args.db)
    landing_dir = project_root / 'landing'

    # Check paths
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print(f"   Available databases:")
        for db_file in project_root.glob('*.db'):
            print(f"     - {db_file.name}")
        sys.exit(1)

    if not landing_dir.exists():
        print(f"❌ Landing directory not found: {landing_dir}")
        sys.exit(1)

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        cleanup_on_exit = False
    else:
        output_dir = pathlib.Path(tempfile.mkdtemp(prefix='penn-path-api-'))
        cleanup_on_exit = True

    try:
        # Export database to API structure
        if not args.no_export:
            api_dir = export_database_to_api(str(db_path), output_dir)
        else:
            api_dir = output_dir / 'api' / 'v1'
            if not api_dir.exists():
                print(f"❌ API directory not found: {api_dir}")
                print(f"   Run without --no-export to generate API files")
                sys.exit(1)
            print(f"📁 Using existing API files from: {api_dir}")

        # Copy API directory into landing directory for serving
        landing_api_dir = landing_dir / 'api'
        if landing_api_dir.exists():
            shutil.rmtree(landing_api_dir)
        shutil.copytree(api_dir.parent, landing_api_dir)

        # Serve
        serve(args.port, landing_dir, landing_api_dir / 'v1')

    finally:
        # Cleanup
        if cleanup_on_exit and output_dir.exists():
            print(f"🧹 Cleaning up temp directory: {output_dir}")
            shutil.rmtree(output_dir)

        # Always cleanup landing/api
        landing_api_dir = landing_dir / 'api'
        if landing_api_dir.exists():
            shutil.rmtree(landing_api_dir)


if __name__ == '__main__':
    main()
