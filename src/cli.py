"""
Penn Path Scraper CLI.

Beautiful command-line interface for scraping and searching Penn course data.
"""

import datetime
import pathlib
import sys
import typing

import rich_click as click
import click_didyoumean
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich import box

import src.api_client
import src.export
import src.export_granular
import src.models
import src.persistence
import src.scraper
import src.types


# Configure rich-click for beautiful help output
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"

# Rich console for beautiful output
console = Console()


# Default database path
DEFAULT_DB_PATH = pathlib.Path.home() / ".penn-scraper" / "courses.db"


class DidYouMeanGroup(click_didyoumean.DYMGroup):
    """Click group with 'Did you mean?' suggestions."""
    pass


@click.group(cls=DidYouMeanGroup)
@click.option(
    "--db",
    default=str(DEFAULT_DB_PATH),
    type=click.Path(),
    help="Path to SQLite database",
    show_default=True,
)
@click.pass_context
def cli(ctx: click.Context, db: str) -> None:
    """
    [bold cyan]Penn Path Scraper[/bold cyan] - Scrape and search Penn course catalog.

    A beautiful CLI for collecting longitudinal course enrollment data from Penn's course catalog.
    """
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db

    # Ensure database directory exists
    db_path = pathlib.Path(db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database if it doesn't exist
    if not db_path.exists():
        with console.status("[bold green]Initializing database..."):
            src.persistence.initialize_database(str(db_path))
        console.print("✅ [green]Database initialized successfully![/green]\n")


@cli.command()
@click.argument("term", required=False)
@click.option(
    "--schools",
    "-s",
    help="Comma-separated school codes (e.g., E,W,A). Default: all schools",
)
@click.option(
    "--next-term",
    is_flag=True,
    help="Also scrape the next term (for advance registration data)",
)
@click.option(
    "--no-snapshots",
    is_flag=True,
    help="Skip creating enrollment snapshots",
)
@click.option(
    "--rate-limit",
    "-r",
    default=0.5,
    type=float,
    help="Delay between API requests in seconds",
    show_default=True,
)
@click.pass_context
def scrape(
    ctx: click.Context,
    term: typing.Optional[str],
    schools: typing.Optional[str],
    next_term: bool,
    no_snapshots: bool,
    rate_limit: float,
) -> None:
    """
    Scrape course data from Penn's catalog.

    TERM is the term code (e.g., 202530 for Fall 2025).
    If not provided, scrapes the current term.
    """
    # Auto-detect term if not provided
    if term is None:
        term = src.api_client.get_current_term()
        console.print(f"📅 [cyan]Auto-detected term:[/cyan] {term} ({src.types.format_term_code(term)})\n")

    # Parse schools
    school_codes = None
    if schools:
        school_codes = [s.strip().upper() for s in schools.split(",")]

    # Initialize API client and scraper
    api_client = src.api_client.PennCoursesAPIClient(rate_limit_delay=rate_limit)
    scraper = src.scraper.CourseScraper(
        api_client=api_client,
        db_path=ctx.obj["db_path"],
    )

    # Determine terms to scrape
    terms_to_scrape = [term]
    if next_term:
        next_term_code = src.api_client.get_next_term(term)
        terms_to_scrape.append(next_term_code)
        console.print(f"📅 [cyan]Also scraping next term:[/cyan] {next_term_code} ({src.types.format_term_code(next_term_code)})\n")

    # Scrape each term
    for term_code in terms_to_scrape:
        console.print(Panel(
            f"[bold]Scraping {src.types.format_term_code(term_code)}[/bold]",
            border_style="cyan"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching course list...", total=None)

            # Create progress callback
            def update_progress(current: int, total: int) -> None:
                progress.update(task, description=f"Processing courses", completed=current, total=total)

            result = scraper.scrape_term(
                term=term_code,
                schools=school_codes,
                create_snapshots=not no_snapshots,
                progress_callback=update_progress,
            )

            progress.update(task, description="Complete!", completed=100, total=100)

        # Display results
        _display_scrape_results(result)


@cli.command()
@click.argument("query", required=False)
@click.option(
    "--term",
    "-t",
    help="Filter by term code (e.g., 202530)",
)
@click.option(
    "--limit",
    "-n",
    default=20,
    help="Maximum number of results to show",
    show_default=True,
)
@click.pass_context
def search(
    ctx: click.Context,
    query: typing.Optional[str],
    term: typing.Optional[str],
    limit: int,
) -> None:
    """
    Search for courses in the database.

    QUERY can be a course code (e.g., CIS 1210), instructor name, or keyword.
    If no query is provided, shows an interactive prompt.
    """
    # Connect to database
    db_path = ctx.obj["db_path"]
    if not pathlib.Path(db_path).exists():
        console.print("❌ [red]Database not found. Run 'scrape' first![/red]")
        sys.exit(1)

    src.models.db.init(db_path)
    src.models.db.connect()

    # Interactive query if not provided
    if query is None:
        query = click.prompt("🔍 Search for courses", type=str)

    # Build search query - join with instructors to search by name
    import peewee

    query_obj = (
        src.models.Course
        .select()
        .join(src.models.CourseInstructor, peewee.JOIN.LEFT_OUTER)
        .join(src.models.Instructor, peewee.JOIN.LEFT_OUTER)
    )

    # Add filters
    if term:
        query_obj = query_obj.where(src.models.Course.term == term)

    # Search in code, title, description, or instructor name
    search_condition = (
        src.models.Course.code.contains(query.upper()) |
        src.models.Course.title.contains(query) |
        src.models.Course.description.contains(query) |
        src.models.Instructor.name.contains(query)
    )
    query_obj = query_obj.where(search_condition)

    # Execute query with distinct to avoid duplicates from joins
    results = list(query_obj.distinct().limit(limit))

    if not results:
        console.print(f"\n❌ [yellow]No courses found matching '{query}'[/yellow]\n")
        sys.exit(0)

    # Display results in a beautiful table
    _display_course_table(results, limit)

    src.models.db.close()


@cli.command()
@click.option(
    "--school",
    "-s",
    default="E",
    help="School code to demo scrape",
    show_default=True,
)
@click.pass_context
def demo(ctx: click.Context, school: str) -> None:
    """
    🎬 Demo mode: Scrape a school and interactively search results.

    This is a quick demo that scrapes one school and lets you search through it.
    Perfect for testing and demonstration purposes!
    """
    school = school.upper()

    # Get school name
    school_name = next(
        (s["name"] for s in src.types.SCHOOLS if s["code"] == school),
        f"School {school}"
    )

    console.print(Panel.fit(
        f"[bold cyan]🎬 Demo Mode[/bold cyan]\n\n"
        f"Scraping: [yellow]{school_name}[/yellow]\n"
        f"Current term: [green]{src.types.format_term_code(src.api_client.get_current_term())}[/green]",
        border_style="cyan",
        box=box.DOUBLE
    ))

    # Initialize and scrape
    api_client = src.api_client.PennCoursesAPIClient()
    scraper = src.scraper.CourseScraper(
        api_client=api_client,
        db_path=ctx.obj["db_path"],
    )

    term = src.api_client.get_current_term()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching course list...", total=None)

        def update_progress(current: int, total: int) -> None:
            progress.update(task, description=f"Processing courses", completed=current, total=total)

        result = scraper.scrape_school(
            term=term,
            school_code=school,
            create_snapshots=True,
            progress_callback=update_progress,
        )

    console.print(f"\n✅ [green]Scraped {result['courses_saved']} courses![/green]\n")

    # Interactive search loop
    src.models.db.init(ctx.obj["db_path"])
    src.models.db.connect()

    console.print("[bold]🔍 Now you can search through the courses![/bold]")
    console.print("[dim]Type 'exit' or 'quit' to stop. Search works for course codes, titles, or instructor names![/dim]\n")

    while True:
        try:
            query = click.prompt("Search", default="", show_default=False)

            if query.lower() in ["exit", "quit", "q", ""]:
                break

            # Search with instructor support
            import peewee

            results = list(
                src.models.Course.select()
                .join(src.models.CourseInstructor, peewee.JOIN.LEFT_OUTER)
                .join(src.models.Instructor, peewee.JOIN.LEFT_OUTER)
                .where(
                    (src.models.Course.term == term) &
                    (
                        src.models.Course.code.contains(query.upper()) |
                        src.models.Course.title.contains(query) |
                        src.models.Instructor.name.contains(query)
                    )
                )
                .distinct()
                .limit(10)
            )

            if results:
                _display_course_table(results, max_results=10)
            else:
                console.print(f"[yellow]No results for '{query}'[/yellow]\n")

        except (KeyboardInterrupt, EOFError):
            break

    src.models.db.close()
    console.print("\n[cyan]👋 Thanks for using Penn Path Scraper![/cyan]")


@cli.command()
@click.argument("course_code")
@click.option(
    "--term",
    "-t",
    help="Term code (e.g., 202530). If not provided, uses most recent.",
)
@click.pass_context
def track(ctx: click.Context, course_code: str, term: typing.Optional[str]) -> None:
    """
    📈 Track enrollment history for a course.

    Shows enrollment changes over time with snapshots.
    """
    # Connect to database
    db_path = ctx.obj["db_path"]
    if not pathlib.Path(db_path).exists():
        console.print("❌ [red]Database not found. Run 'scrape' first![/red]")
        sys.exit(1)

    src.models.db.init(db_path)
    src.models.db.connect()

    # Find course
    query = src.models.Course.select().where(
        src.models.Course.code == course_code.upper()
    )

    if term:
        query = query.where(src.models.Course.term == term)

    query = query.order_by(src.models.Course.term.desc())

    course = query.first()

    if not course:
        console.print(f"❌ [red]Course '{course_code}' not found![/red]")
        src.models.db.close()
        sys.exit(1)

    # Display course info
    console.print(Panel(
        f"[bold]{course.code} - {course.title}[/bold]\n"
        f"[dim]{src.types.format_term_code(course.term.code)} • Section {course.section}[/dim]",
        border_style="cyan"
    ))

    # Get enrollment history
    snapshots = list(
        src.models.EnrollmentSnapshot.select()
        .where(src.models.EnrollmentSnapshot.course == course)
        .order_by(src.models.EnrollmentSnapshot.timestamp)
    )

    if not snapshots:
        console.print("\n[yellow]No enrollment snapshots found for this course.[/yellow]")
        console.print("[dim]Snapshots are created during each scrape.[/dim]\n")
    else:
        _display_enrollment_history(snapshots, course)

    src.models.db.close()


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """
    📊 Show database statistics.

    Display overview of scraped data.
    """
    # Connect to database
    db_path = ctx.obj["db_path"]
    if not pathlib.Path(db_path).exists():
        console.print("❌ [red]Database not found. Run 'scrape' first![/red]")
        sys.exit(1)

    src.models.db.init(db_path)
    src.models.db.connect()

    # Gather stats
    total_courses = src.models.Course.select().count()
    total_terms = src.models.Term.select().count()
    total_instructors = src.models.Instructor.select().count()
    total_snapshots = src.models.EnrollmentSnapshot.select().count()

    # Get latest scrape info
    latest_scrape = (
        src.models.Course.select()
        .order_by(src.models.Course.last_scraped.desc())
        .first()
    )

    # Display stats
    table = Table(title="📊 Database Statistics", box=box.ROUNDED, border_style="cyan")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Total Courses", str(total_courses))
    table.add_row("Total Terms", str(total_terms))
    table.add_row("Total Instructors", str(total_instructors))
    table.add_row("Enrollment Snapshots", str(total_snapshots))

    if latest_scrape:
        # Handle both datetime and string (SQLite sometimes returns strings)
        last_scraped = latest_scrape.last_scraped
        if isinstance(last_scraped, str):
            table.add_row("Last Scrape", last_scraped)
        else:
            table.add_row("Last Scrape", last_scraped.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(table)
    console.print()

    # Show terms
    terms = list(src.models.Term.select().order_by(src.models.Term.code.desc()))
    if terms:
        console.print("[bold cyan]📅 Available Terms:[/bold cyan]")
        for term in terms:
            course_count = src.models.Course.select().where(src.models.Course.term == term).count()
            console.print(f"  • {term.name} ({term.code}): [green]{course_count}[/green] courses")

    console.print()
    src.models.db.close()


# =============================================================================
# Helper Functions
# =============================================================================

def _display_scrape_results(result: src.scraper.TermScrapeResult) -> None:
    """Display scrape results in a beautiful table."""
    table = Table(
        title=f"Scrape Results - {src.types.format_term_code(result['term'])}",
        box=box.ROUNDED,
        border_style="cyan"
    )

    table.add_column("School", style="cyan", no_wrap=True)
    table.add_column("Found", justify="right", style="yellow")
    table.add_column("Saved", justify="right", style="green")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Duration", justify="right", style="dim")

    for school_result in result["school_results"]:
        # Get school name
        school_name = next(
            (s["name"] for s in src.types.SCHOOLS if s["code"] == school_result["school_code"]),
            school_result["school_code"]
        )

        # Truncate long school names
        if len(school_name) > 40:
            school_name = school_name[:37] + "..."

        table.add_row(
            school_name,
            str(school_result["courses_found"]),
            str(school_result["courses_saved"]),
            str(school_result["errors_count"]),
            f"{school_result['duration_seconds']:.2f}s"
        )

    console.print(table)

    # Summary
    console.print(f"\n[bold green]✅ Total: {result['total_courses_saved']}/{result['total_courses_found']} courses saved[/bold green]")
    if result["total_errors"] > 0:
        console.print(f"[bold red]⚠️  {result['total_errors']} errors occurred[/bold red]")
    console.print(f"[dim]Completed in {result['duration_seconds']:.2f}s[/dim]\n")


def _display_course_table(courses: typing.List[src.models.Course], max_results: int) -> None:
    """Display courses in a beautiful table."""
    table = Table(
        title=f"🔍 Search Results ({len(courses)} courses)",
        box=box.ROUNDED,
        border_style="cyan"
    )

    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Term", style="dim")
    table.add_column("Enrollment", justify="right", style="yellow")
    table.add_column("Seats", justify="right", style="green")

    for course in courses:
        enrollment_str = f"{course.enrolled}/{course.max_enrollment}"

        table.add_row(
            f"{course.code} {course.section}",
            course.title[:50] + "..." if len(course.title) > 50 else course.title,
            src.types.format_term_code(course.term.code),
            enrollment_str,
            str(course.seats_available)
        )

    console.print(table)
    console.print()


def _display_enrollment_history(
    snapshots: typing.List[src.models.EnrollmentSnapshot],
    course: src.models.Course
) -> None:
    """Display enrollment history with a sparkline or table."""
    console.print(f"\n[bold]📈 Enrollment History ({len(snapshots)} snapshots)[/bold]\n")

    table = Table(box=box.SIMPLE, show_header=True, border_style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Time", style="dim")
    table.add_column("Enrolled", justify="right", style="yellow")
    table.add_column("Capacity", justify="right", style="green")
    table.add_column("Fill Rate", justify="right", style="magenta")

    for snapshot in snapshots:
        fill_rate = (snapshot.enrolled / snapshot.capacity * 100) if snapshot.capacity > 0 else 0

        table.add_row(
            snapshot.timestamp.strftime("%Y-%m-%d"),
            snapshot.timestamp.strftime("%H:%M:%S"),
            str(snapshot.enrolled),
            str(snapshot.capacity),
            f"{fill_rate:.1f}%"
        )

    console.print(table)
    console.print()


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    default="./data",
    help="Output directory for JSON files",
    show_default=True,
)
@click.option(
    "--term",
    "-t",
    help="Export specific term only (monolithic mode only)",
)
@click.option(
    "--monolithic",
    is_flag=True,
    help="Use monolithic export (one file per term) instead of granular structure",
)
@click.pass_context
def export(ctx: click.Context, output_dir: str, term: typing.Optional[str], monolithic: bool) -> None:
    """
    📦 Export course data to JSON files.

    **Default**: Granular structure following ADR-0002 Option C
    - Separate files per course with metadata + enrollment history
    - Search indexes for instructors and departments
    - Efficient updates (only changed files modified)

    **Monolithic mode** (--monolithic): Simple one-file-per-term export
    - Faster for initial setup
    - Easier to consume as single file
    - Larger git diffs on updates
    """
    # Initialize database (read-only)
    src.persistence.initialize_database(ctx.obj["db_path"])

    output_path = pathlib.Path(output_dir)

    if monolithic:
        # Monolithic export (original behavior)
        if term:
            # Export single term
            console.print(f"\n[bold cyan]📦 Exporting term {term} (monolithic)...[/bold cyan]\n")

            try:
                term_file = output_path / f"{term}.json"
                src.export.export_term_to_json(term, str(term_file))

                console.print(f"✅ Exported to: [green]{term_file}[/green]")

            except src.models.Term.DoesNotExist:
                console.print(f"[red]❌ Error: Term {term} not found in database[/red]")
                sys.exit(1)

        else:
            # Export all terms (monolithic)
            console.print("[bold cyan]📦 Exporting all terms (monolithic)...[/bold cyan]\n")

            term_count = src.models.Term.select().count()

            if term_count == 0:
                console.print("[yellow]⚠️  No terms found in database[/yellow]")
                sys.exit(0)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Exporting {term_count} terms...", total=term_count)

                src.export.export_all_terms(str(output_path))

                progress.update(task, completed=term_count)

            console.print(f"\n✅ Exported {term_count} terms to: [green]{output_path}[/green]")
            console.print(f"📄 Index file: [green]{output_path / 'index.json'}[/green]\n")

    else:
        # Granular export (ADR-0002 Option C)
        if term:
            console.print("[yellow]⚠️  --term flag only works with --monolithic mode[/yellow]")
            console.print("[dim]Granular export always exports all data for consistency[/dim]\n")

        console.print("[bold cyan]📦 Exporting granular structure (ADR-0002 Option C)...[/bold cyan]\n")

        with console.status("[bold green]Building API structure..."):
            src.export_granular.export_granular_structure(str(output_path))

        console.print(f"\n✅ [green]Exported granular API structure to: {output_path / 'api' / 'v1'}[/green]")
        console.print(f"📄 Master index: [green]{output_path / 'api' / 'v1' / 'index.json'}[/green]")
        console.print(f"📁 Course files: [green]{output_path / 'api' / 'v1' / 'courses'}[/green]")
        console.print(f"📅 Term files: [green]{output_path / 'api' / 'v1' / 'terms'}[/green]")
        console.print(f"🔍 Search indexes: [green]{output_path / 'api' / 'v1' / 'search'}[/green]\n")


if __name__ == "__main__":
    cli()
