"""Agent commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table
from zksato_api.llm_clients import (
    LocalLLMBackend,
    LocalLLMClient,
    LocalLLMConfig,
)

app = typer.Typer(name="agent", help="Agent commands")
console = Console()


@app.command("start")
def start_agent(
    name: str = typer.Argument(..., help="Agent name"),
    subaccount: str = typer.Option("default", "--subaccount", "-s", help="Sub-account"),
    model: str = typer.Option("llama3.2:3b", "--model", "-m", help="Model name"),
    backend: str = typer.Option(
        "ollama", "--backend", "-b", help="Backend (ollama, llamacpp, vllm, tgi)"
    ),
    base_url: str = typer.Option("http://localhost:11434", "--base-url", help="Backend base URL"),
    thinking: str = typer.Option(
        "high", "--thinking", "-t", help="Thinking level (low/medium/high/xhigh)"
    ),
    timeout: float = typer.Option(60.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Start an agent with local LLM."""
    console.print(f"[green]Starting agent:[/green] {name} (subaccount: {subaccount})")
    console.print(f"  Model: {model} (backend: {backend})")
    console.print(f"  Base URL: {base_url}")
    console.print(f"  Thinking: {thinking}")
    console.print(f"  Timeout: {timeout}s")

    asyncio.run(_run_agent(name, subaccount, model, backend, base_url, thinking, timeout))


async def _run_agent(
    name: str,
    subaccount: str,
    model: str,
    backend: str,
    base_url: str,
    thinking: str,
    timeout: float = 60.0,
) -> None:
    """Run the agent loop."""
    try:
        backend_enum = LocalLLMBackend(backend.lower())
    except ValueError:
        console.print(f"[red]Invalid backend: {backend}[/red]")
        return

    llm_config = LocalLLMConfig(
        backend=backend_enum,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
    )
    llm_client = LocalLLMClient(config=llm_config)

    try:
        # Test the LLM connection
        console.print("[cyan]Testing LLM connection...[/cyan]")
        await llm_client.initialize()
        if llm_client.is_available:
            console.print("[green]✓ LLM backend connected[/green]")
        else:
            console.print("[yellow]⚠ LLM backend not available, running in stub mode[/yellow]")

        # Test code generation
        console.print("\n[cyan]Testing code generation...[/cyan]")
        response = await llm_client.generate_code(
            prompt="Create a simple function to calculate moving average",
            language="python",
            thinking_level=thinking.upper(),
        )
        console.print(f"[green]Generated code:[/green]\n{response.content[:500]}...")

        console.print(f"\n[green]Agent {subaccount} started successfully![/green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping agent...[/yellow]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
    finally:
        await llm_client.close()


@app.command("stop")
def stop_agent(name: str = typer.Argument(..., help="Agent name")) -> None:
    """Stop an agent."""
    console.print(f"[red]Stopping agent:[/red] {name}")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command("list")
def list_agents() -> None:
    """List agents."""
    console.print("[yellow]No agents running[/yellow]")


@app.command("skills")
def list_skills() -> None:
    """List available skills."""
    table = Table(title="Available Skills")
    table.add_column("Name")
    table.add_column("Description")
    skills = [
        ("get_quote", "Get real-time quote"),
        ("place_order", "Place an order"),
        ("get_positions", "Get positions"),
        ("cancel_order", "Cancel an order"),
        ("check_risk", "Check risk"),
    ]
    for skill_name, desc in skills:
        table.add_row(skill_name, desc)
    console.print(table)


@app.command("chat")
def chat_with_agent(
    name: str = typer.Argument(..., help="Agent name"),
    message: str = typer.Argument(..., help="Message to send"),
    subaccount: str = typer.Option("default", "--subaccount", "-s", help="Sub-account"),
    model: str = typer.Option("llama3.2:3b", "--model", "-m", help="Model name"),
    backend: str = typer.Option(
        "ollama", "--backend", "-b", help="Backend (ollama, llamacpp, vllm, tgi)"
    ),
    base_url: str = typer.Option("http://localhost:11434", "--base-url", help="Backend base URL"),
    thinking: str = typer.Option(
        "high", "--thinking", "-t", help="Thinking level (low/medium/high/xhigh)"
    ),
    timeout: float = typer.Option(60.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Send a message to an agent and get a response."""
    console.print(f"[cyan]Chatting with agent {name}...[/cyan]")
    asyncio.run(
        _chat_with_agent(name, subaccount, message, model, backend, base_url, thinking, timeout)
    )


async def _chat_with_agent(
    name: str,
    subaccount: str,
    message: str,
    model: str,
    backend: str,
    base_url: str,
    thinking: str,
    timeout: float = 60.0,
) -> None:
    """Send a message to the agent and get response."""
    try:
        backend_enum = LocalLLMBackend(backend.lower())
    except ValueError:
        console.print(f"[red]Invalid backend: {backend}[/red]")
        return

    config = LocalLLMConfig(
        backend=backend_enum,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
    )
    client = LocalLLMClient(config=config)

    try:
        await client.initialize()
        if not client.is_available:
            console.print("[yellow]⚠ LLM backend not available, running in stub mode[/yellow]")
    except Exception as exc:
        console.print(f"[red]Failed to initialize LLM client: {exc}[/red]")
        return

    # Send message
    try:
        response = await client.generate(
            messages=[
                {"role": "system", "content": "You are a helpful trading assistant."},
                {"role": "user", "content": message},
            ],
        )
        console.print(f"\n[bold cyan]Agent {name}:[/bold cyan]")
        console.print(response.content)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
    finally:
        await client.close()


@app.command("generate-code")
def generate_code(
    prompt: str = typer.Argument(..., help="Code generation prompt"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language"),
    model: str = typer.Option("llama3.2:3b", "--model", "-m", help="Model name"),
    backend: str = typer.Option("ollama", "--backend", "-b", help="Backend"),
    base_url: str = typer.Option("http://localhost:11434", "--base-url", help="Backend base URL"),
    thinking: str = typer.Option("high", "--thinking", "-t", help="Thinking level"),
    timeout: float = typer.Option(60.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Generate code using local LLM."""
    console.print(f"[cyan]Generating {language} code...[/cyan]")
    asyncio.run(_generate_code(prompt, language, model, backend, base_url, thinking, timeout))


async def _generate_code(
    prompt: str,
    language: str,
    model: str,
    backend: str,
    base_url: str,
    thinking: str,
    timeout: float = 60.0,
) -> None:
    """Generate code using local LLM."""
    try:
        backend_enum = LocalLLMBackend(backend.lower())
    except ValueError:
        console.print(f"[red]Invalid backend: {backend}[/red]")
        return

    config = LocalLLMConfig(
        backend=backend_enum,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
    )
    client = LocalLLMClient(config=config)

    try:
        await client.initialize()
        if client.is_available:
            console.print("[green]✓ LLM backend connected[/green]")
        else:
            console.print("[yellow]⚠ LLM backend not available, running in stub mode[/yellow]")

        response = await client.generate_code(
            prompt=prompt,
            language=language,
            thinking_level=thinking.upper(),
        )

        console.print(f"\n[bold cyan]Generated {language} code:[/bold cyan]")
        console.print(response.content)

        console.print(
            f"\n[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out | "
            f"Latency: {response.latency_seconds:.2f}s[/dim]"
        )
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
    finally:
        await client.close()


@app.command("analyze-code")
def analyze_code(
    code: str = typer.Argument(..., help="Code to analyze (or file path)"),
    language: str = typer.Option("python", "--language", "-l", help="Programming language"),
    model: str = typer.Option("llama3.2:3b", "--model", "-m", help="Model name"),
    backend: str = typer.Option("ollama", "--backend", "-b", help="Backend"),
    base_url: str = typer.Option("http://localhost:11434", "--base-url", help="Backend base URL"),
    thinking: str = typer.Option("xhigh", "--thinking", "-t", help="Thinking level"),
    timeout: float = typer.Option(60.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Analyze code for bugs, security issues, and improvements."""
    console.print(f"[cyan]Analyzing {language} code...[/cyan]")
    asyncio.run(_analyze_code(code, language, model, backend, base_url, thinking, timeout))


async def _analyze_code(
    code: str,
    language: str,
    model: str,
    backend: str,
    base_url: str,
    thinking: str,
    timeout: float = 60.0,
) -> None:
    """Analyze code using local LLM."""
    try:
        backend_enum = LocalLLMBackend(backend.lower())
    except ValueError:
        console.print(f"[red]Invalid backend: {backend}[/red]")
        return

    config = LocalLLMConfig(
        backend=backend_enum,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
    )
    client = LocalLLMClient(config=config)

    try:
        await client.initialize()
        if client.is_available:
            console.print("[green]✓ LLM backend connected[/green]")
        else:
            console.print("[yellow]⚠ LLM backend not available, running in stub mode[/yellow]")

        response = await client.analyze_code(code=code, language=language)

        console.print("\n[bold cyan]Analysis Result:[/bold cyan]")
        console.print(response.content)

        console.print(
            f"\n[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out | "
            f"Latency: {response.latency_seconds:.2f}s[/dim]"
        )
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
    finally:
        await client.close()


@app.command("verify-test")
def verify_test(
    test_code: str = typer.Argument(..., help="Test code (or file path)"),
    source_code: str = typer.Argument(..., help="Source code (or file path)"),
    model: str = typer.Option("llama3.2:3b", "--model", "-m", help="Model name"),
    backend: str = typer.Option("ollama", "--backend", "-b", help="Backend"),
    base_url: str = typer.Option("http://localhost:11434", "--base-url", help="Backend base URL"),
    thinking: str = typer.Option("high", "--thinking", "-t", help="Thinking level"),
    timeout: float = typer.Option(60.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Verify test coverage against source code."""
    console.print("[cyan]Verifying test coverage...[/cyan]")
    asyncio.run(_verify_test(test_code, source_code, model, backend, base_url, thinking, timeout))


async def _verify_test(
    test_code: str,
    source_code: str,
    model: str,
    backend: str,
    base_url: str,
    thinking: str,
    timeout: float = 60.0,
) -> None:
    """Verify test coverage using local LLM."""
    try:
        backend_enum = LocalLLMBackend(backend.lower())
    except ValueError:
        console.print(f"[red]Invalid backend: {backend}[/red]")
        return

    config = LocalLLMConfig(
        backend=backend_enum,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
    )
    client = LocalLLMClient(config=config)

    try:
        await client.initialize()
        if client.is_available:
            console.print("[green]✓ LLM backend connected[/green]")
        else:
            console.print("[yellow]⚠ LLM backend not available, running in stub mode[/yellow]")

        response = await client.verify_test(test_code=test_code, source_code=source_code)

        console.print("\n[bold cyan]Verification Result:[/bold cyan]")
        console.print(response.content)

        console.print(
            f"\n[dim]Tokens: {response.input_tokens} in, {response.output_tokens} out | "
            f"Latency: {response.latency_seconds:.2f}s[/dim]"
        )
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
    finally:
        await client.close()


if __name__ == "__main__":
    app()
