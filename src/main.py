"""
Space Operations Co-Pilot — CLI Entry Point.

Interactive mission control interface for satellite tracking
and observation planning.
"""

from __future__ import annotations

import logging
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import IntPrompt

from src.agents.orchestrator import FlightDirector
from src.tools.map_generator import generate_satellite_map, start_live_tracking

# Configure logging (only show warnings+ to avoid cluttering the rich interface)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("SATCOM-CoPilot")

app = typer.Typer(add_completion=False, help="Space Operations Co-Pilot CLI")
console = Console()

BANNER_TEXT = """\
[bold #FF5500]   ███            ███   [/bold #FF5500]
[bold #FF8800]   ███            ███   [/bold #FF8800]
[bold #FFBB00]   ███    ████    ███   [/bold #FFBB00]
[bold #FFEE00]   ███  ████████  ███   [/bold #FFEE00]
[bold #99EEFF]    ██  ████████  ██    [/bold #99EEFF]
[bold #66CCFF]  ████████████████████  [/bold #66CCFF]
[bold #33AAFF]    ████████████████    [/bold #33AAFF]
[bold #0088FF]          ████          [/bold #0088FF]
[bold #0066CC]         ██  ██         [/bold #0066CC]

   [bold white]SPACE OPERATIONS CO-PILOT  (SATCOM-CoPilot)[/bold white]          
                                                              
   Autonomous Satellite Trajectory & Observation Planner     
                                                              
   Console Agents:                                           
     • Flight Director (FD) ............ [bold green]ONLINE[/bold green]
     • GNC Console ..................... [bold green]ONLINE[/bold green]
     • Weather & COMM Console .......... [bold green]ONLINE[/bold green]
     • QA / Evaluation Agent ........... [bold green]ONLINE[/bold green]
                                                              
   Defaults:                                                 
     Satellite: ISS (ZARYA) — NORAD 25544                   
     Location:  Bengaluru, India (12.97°N, 77.59°E)         
     Window:    72 hours                                     
                                                              
   Type your query or 'quit' to exit.\
"""

def print_banner() -> None:
    panel = Panel(
        Text.from_markup(BANNER_TEXT, justify="left"),
        title="[bold cyan]SPACE OPS CO-PILOT[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)

def render_passes(passes: list, observer_city: str) -> None:
    if not passes:
        console.print(Panel("[yellow]No passes found in the specified time window.[/yellow]", border_style="yellow"))
        return

    table = Table(
        title=f"🛰️ Satellite Pass Windows for {observer_city or 'Observer'}",
        title_style="bold cyan",
        border_style="cyan",
        header_style="bold white"
    )
    table.add_column("Pass", style="magenta", justify="center")
    table.add_column("Rating", justify="center")
    table.add_column("Rise (UTC) & Azimuth", style="green")
    table.add_column("Peak (UTC) & Elevation", style="cyan")
    table.add_column("Set (UTC) & Azimuth", style="red")
    table.add_column("Duration", style="yellow")
    table.add_column("Sunlit", style="yellow")

    for pw in passes:
        pn = str(pw.get("pass_number", "?"))
        rating = pw.get("visibility_rating", "")
        rating_color = "green" if rating == "EXCELLENT" else "yellow" if rating == "GOOD" else "red"
        
        rise = str(pw.get("rise_utc", ""))[:19]
        rise_az = pw.get("rise_azimuth_deg", 0)
        culm = str(pw.get("culmination_utc", ""))[:19]
        culm_el = pw.get("max_elevation_deg", 0)
        sett = str(pw.get("set_utc", ""))[:19]
        set_az = pw.get("set_azimuth_deg", 0)
        
        dur = pw.get("duration_seconds", 0)
        dur_m, dur_s = divmod(dur, 60)
        sunlit = "🌞 YES" if pw.get("is_sunlit") else "🌑 NO"
        
        table.add_row(
            f"#{pn}",
            f"[{rating_color} bold]{rating}[/{rating_color} bold]",
            f"{rise}\nAZ: {rise_az:.1f}°",
            f"{culm}\nEL: {culm_el:.1f}°",
            f"{sett}\nAZ: {set_az:.1f}°",
            f"{dur_m}m {dur_s}s",
            sunlit
        )
    
    console.print(table)

def render_telemetry(position: dict, satellite: str, observer_city: str) -> None:
    if not position:
        console.print("[red]No telemetry data available.[/red]")
        return
        
    table = Table(
        title=f"📡 LIVE TELEMETRY: {satellite} over {observer_city or 'Observer'}",
        title_style="bold magenta",
        border_style="magenta",
        show_header=False
    )
    table.add_column("Metric", style="bold cyan", justify="right")
    table.add_column("Value", style="white", justify="left")
    
    table.add_row("Timestamp (UTC)", str(position.get("timestamp_utc")))
    table.add_row("Latitude", f"{position.get('latitude', 0):.4f}°")
    table.add_row("Longitude", f"{position.get('longitude', 0):.4f}°")
    table.add_row("Altitude", f"{position.get('altitude_km', 0):.1f} km")
    table.add_row("Speed", f"{position.get('speed_kmh', 0):.1f} km/h")
    
    sky = position.get("sky_position", "")
    comp = position.get("compass_direction", "")
    el = position.get("altitude_deg", 0)
    az = position.get("azimuth_deg", 0)
    
    table.add_row("Sky Position", f"{sky} (EL: {el:.1f}°)")
    table.add_row("Compass", f"{comp} (AZ: {az:.1f}°)")
    table.add_row("Distance", f"{position.get('distance_km', 0):.1f} km")
    table.add_row("Sunlit", "🌞 YES" if position.get("is_sunlit") else "🌑 NO")
    
    console.print(table)

def render_weather(weather: dict) -> None:
    if not weather or not weather.get("reports"):
        return
    
    reports = weather.get("reports", [])
    console.print("\n[bold cyan]📡 WEATHER & COMM CONSOLE — VISIBILITY REPORT[/bold cyan]")
    for wr in reports:
        rec = wr.get("recommendation", "")
        console.print(f"   {rec}")

def print_result(result: dict) -> None:
    status = result.get("status", "UNKNOWN")
    
    if status == "HELP":
        console.print(Panel(result.get("message", ""), title="[bold blue]Flight Director Help[/bold blue]", border_style="blue"))
        return
        
    if status == "ERROR":
        code = result.get("error_code", "UNKNOWN_ERROR")
        msg = result.get("error_message", "An unknown error occurred.")
        console.print(Panel(msg, title=f"[bold red]🚫 FLIGHT DIRECTOR — {code}[/bold red]", border_style="red"))
        return
        
    intent = result.get("intent")
    observer = result.get("observer", {})
    obs_city = observer.get("city", "")
    satellite = result.get("satellite", "")
    
    console.print("")
    
    if intent in ("TRACK_PASS", "VISIBILITY_CHECK"):
        passes = result.get("passes", [])
        render_passes(passes, obs_city)
        render_weather(result.get("weather"))
        
    elif intent in ("LIVE_TELEMETRY", "VISUALIZE_MAP"):
        position = result.get("position", {})
        render_telemetry(position, satellite, obs_city)
        
        # Launch live tracking dashboard for VISUALIZE_MAP intent
        if intent == "VISUALIZE_MAP" and position:
            console.print("\n[bold cyan]\U0001f6f0\ufe0f  Available Satellites for Tracking:[/bold cyan]")
            
            options = [
                ("ISS (ZARYA)", 25544),
                ("HST (Hubble)", 20580),
                ("CSS (Tiangong)", 48274),
                ("GOES 16", 41866),
                ("LANDSAT 9", 49260),
            ]
            
            for i, (name, _) in enumerate(options, 1):
                console.print(f"  [bold cyan]{i}.[/bold cyan] {name}")
            
            all_idx = len(options) + 1
            console.print(f"  [bold cyan]{all_idx}.[/bold cyan] ALL SATELLITES (Fleet Tracking)")
            
            choice = IntPrompt.ask(
                "\nSelect an option to launch",
                choices=[str(x) for x in range(1, all_idx + 1)],
                show_choices=False
            )
            
            if choice == all_idx:
                fleet = options
            else:
                fleet = [options[choice - 1]]

            fleet_names = ", ".join(name for name, _ in fleet)
            fleet_count = len(fleet)

            console.print(
                f"\n[bold magenta]\U0001f5fa\ufe0f  Launching live {'fleet' if fleet_count > 1 else 'satellite'} "
                f"tracker in your browser...[/bold magenta]"
            )
            console.print(
                f"[dim]   Tracking {fleet_count} satellite(s): {fleet_names}[/dim]"
            )
            console.print(
                "[dim]   The map auto-refreshes every 20 seconds with live SGP4 data.[/dim]"
            )
            console.print(
                "[bold yellow]   Press Ctrl+C to stop live tracking and return to the prompt.[/bold yellow]\n"
            )
            try:
                start_live_tracking(
                    satellites=fleet,
                    observer_lat=observer.get("latitude", 12.9716),
                    observer_lon=observer.get("longitude", 77.5946),
                    observer_elevation_m=observer.get("elevation_m", 0),
                    observer_city=obs_city,
                    refresh_seconds=20,
                )
            except KeyboardInterrupt:
                console.print(
                    "\n[bold green]\u2705 Live tracking stopped. Returning to mission prompt.[/bold green]"
                )
            except RuntimeError as exc:
                console.print(f"[red]\u26a0\ufe0f  Live tracking failed: {exc}[/red]")
        
    # Print notices
    for notice in result.get("notices", []):
        console.print(f"\n[yellow]ℹ️ {notice}[/yellow]")


@app.command()
def run_cli(query: str = typer.Argument(None, help="Optional single query to execute.")) -> None:
    """Start the interactive Space Operations Co-Pilot."""
    fd = FlightDirector()

    if query:
        with console.status("[bold cyan]Flight Director routing mission...[/bold cyan]", spinner="bouncingBar"):
            result = fd.execute_mission(query)
        print_result(result)
        return

    print_banner()

    while True:
        try:
            query_input = console.input("\n[bold cyan]🛰️  Mission Query > [/bold cyan]").strip()

            if not query_input:
                continue

            if query_input.lower() in ("quit", "exit", "q"):
                console.print("\n[bold green]👋 Flight Director signing off. Clear skies![/bold green]")
                break

            with console.status("[bold cyan]Flight Director routing mission...[/bold cyan]", spinner="bouncingBar"):
                result = fd.execute_mission(query_input)
                
            print_result(result)

        except KeyboardInterrupt:
            console.print("\n\n[bold green]👋 Flight Director signing off. Clear skies![/bold green]")
            break
        except EOFError:
            break


if __name__ == "__main__":
    app()
