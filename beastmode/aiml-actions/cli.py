#!/usr/bin/env python3
"""
AIML Actions CLI - Choose Your Own Adventure DevOps

Main entry point for the AIML Actions system combining:
- AIML pattern matching for structured commands
- LLM fallback for novel situations
- Adventure engine for guided workflows
- GitHub Actions integration for execution
"""

import os
import sys
import json
import readline
from pathlib import Path
from typing import Optional

# Add engine to path
sys.path.insert(0, os.path.dirname(__file__))

from engine.aiml_engine import AIMLActionsEngine, ActionResult
from engine.adventure_engine import AdventureEngine, AdventureResponse, create_sample_adventures
from engine.action_dispatcher import ActionDispatcher


# ═══════════════════════════════════════════════════════════════════════════════
# COLORS AND FORMATTING
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def print_header():
    """Print the AIML Actions header"""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   {Colors.BOLD}🎮 AIML ACTIONS{Colors.RESET}{Colors.CYAN} - Choose Your Own Adventure DevOps          ║
║                                                                   ║
║   Hybrid AIML + LLM + GitHub Actions                              ║
║   Type 'help' for commands, 'quit' to exit                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{Colors.RESET}
""")


def print_response(result: ActionResult):
    """Print an AIML response with formatting"""
    print(f"\n{Colors.GREEN}{result.text}{Colors.RESET}")
    
    if result.action == "workflow" and result.workflow:
        print(f"\n{Colors.YELLOW}[ACTION]{Colors.RESET} Triggering workflow: {Colors.BOLD}{result.workflow}{Colors.RESET}")
        if result.inputs:
            print(f"{Colors.DIM}Inputs: {json.dumps(result.inputs, indent=2)}{Colors.RESET}")
    
    if result.choices:
        print(f"\n{Colors.CYAN}Choices:{Colors.RESET}")
        for i, choice in enumerate(result.choices, 1):
            print(f"  {Colors.BOLD}[{i}]{Colors.RESET} {choice['label']}")
    
    if result.confirm:
        print(f"\n{Colors.YELLOW}[CONFIRM]{Colors.RESET} {result.confirm}")
        print(f"  Type 'yes' to confirm or 'no' to cancel")


def print_adventure_response(response: AdventureResponse):
    """Print an adventure response with formatting"""
    print(f"\n{Colors.CYAN}{'─' * 60}{Colors.RESET}")
    print(f"{Colors.GREEN}{response.text}{Colors.RESET}")
    
    if response.choices:
        print(f"\n{Colors.CYAN}Your choices:{Colors.RESET}")
        for choice in response.choices:
            print(f"  {Colors.BOLD}[{choice['value']}]{Colors.RESET} {choice['label']}")
    
    if response.action:
        print(f"\n{Colors.YELLOW}[ACTION]{Colors.RESET} {response.action}")
        if response.inputs:
            print(f"{Colors.DIM}Inputs: {json.dumps(response.inputs)}{Colors.RESET}")
    
    if response.is_end:
        print(f"\n{Colors.CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.DIM}Adventure complete.{Colors.RESET}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLI
# ═══════════════════════════════════════════════════════════════════════════════

class AIMLActionsCLI:
    """Main CLI for AIML Actions"""
    
    def __init__(self):
        # Get paths
        base_dir = Path(__file__).parent
        patterns_dir = base_dir / "patterns"
        adventures_dir = base_dir / "adventures"
        
        # Create sample adventures if needed
        if not adventures_dir.exists():
            create_sample_adventures(str(adventures_dir))
        
        # Initialize engines
        self.aiml = AIMLActionsEngine(str(patterns_dir) if patterns_dir.exists() else None)
        self.adventure = AdventureEngine(str(adventures_dir) if adventures_dir.exists() else None)
        self.dispatcher = ActionDispatcher()
        
        # State
        self.mode = "normal"
        self.last_action: Optional[ActionResult] = None
    
    def process_input(self, user_input: str) -> bool:
        """
        Process user input and return whether to continue.
        
        Returns False if the user wants to quit.
        """
        user_input = user_input.strip()
        
        if not user_input:
            return True
        
        # Check for quit
        if user_input.lower() in ["quit", "exit", "bye", "q"]:
            print(f"\n{Colors.CYAN}Goodbye! 👋{Colors.RESET}\n")
            return False
        
        # Check for adventure commands
        if user_input.lower() == "cancel" and self.adventure.active:
            response = self.adventure.cancel_adventure()
            print_adventure_response(response)
            return True
        
        # If in adventure mode, process choice
        if self.adventure.active:
            response = self.adventure.process_choice(user_input)
            print_adventure_response(response)
            
            # Execute action if triggered
            if response.action:
                self._execute_action(response.action, response.inputs)
            
            return True
        
        # Check for adventure triggers
        if user_input.lower().startswith("start "):
            adventure_id = user_input[6:].strip()
            response = self.adventure.start_adventure(adventure_id)
            print_adventure_response(response)
            return True
        
        triggered = self.adventure.check_triggers(user_input)
        if triggered:
            response = self.adventure.start_adventure(triggered)
            print_adventure_response(response)
            return True
        
        # Process with AIML engine
        result = self.aiml.respond(user_input)
        
        if result:
            print_response(result)
            self.last_action = result
            
            # Auto-execute in god mode
            if self.mode == "god" and result.action == "workflow":
                self._execute_action(result.workflow, result.inputs)
        else:
            print(f"\n{Colors.DIM}I didn't understand that. Try 'help' for commands.{Colors.RESET}")
        
        return True
    
    def _execute_action(self, workflow: str, inputs: dict = None):
        """Execute a GitHub Actions workflow"""
        print(f"\n{Colors.YELLOW}Dispatching workflow...{Colors.RESET}")
        
        result = self.dispatcher.dispatch_workflow(workflow, inputs or {})
        
        if result.success:
            print(f"{Colors.GREEN}✓ Workflow dispatched successfully!{Colors.RESET}")
            if result.run_url:
                print(f"  Track progress: {result.run_url}")
        else:
            print(f"{Colors.RED}✗ Dispatch failed: {result.error}{Colors.RESET}")
    
    def run(self):
        """Run the interactive CLI"""
        print_header()
        
        # Enable readline history
        histfile = os.path.expanduser("~/.aiml_actions_history")
        try:
            readline.read_history_file(histfile)
        except FileNotFoundError:
            pass
        
        try:
            while True:
                try:
                    # Build prompt
                    if self.adventure.active:
                        prompt = f"{Colors.CYAN}[{self.adventure.current_state.adventure_id}]{Colors.RESET} > "
                    elif self.mode == "god":
                        prompt = f"{Colors.RED}⚡ GOD{Colors.RESET} > "
                    elif self.mode == "beast":
                        prompt = f"{Colors.YELLOW}🦁 BEAST{Colors.RESET} > "
                    else:
                        prompt = f"{Colors.GREEN}>{Colors.RESET} "
                    
                    user_input = input(prompt)
                    
                    if not self.process_input(user_input):
                        break
                
                except KeyboardInterrupt:
                    print(f"\n{Colors.DIM}(Use 'quit' to exit){Colors.RESET}")
                    continue
        
        finally:
            # Save history
            try:
                readline.write_history_file(histfile)
            except:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Non-interactive mode
        command = " ".join(sys.argv[1:])
        cli = AIMLActionsCLI()
        cli.process_input(command)
    else:
        # Interactive mode
        cli = AIMLActionsCLI()
        cli.run()


if __name__ == "__main__":
    main()
