#!/usr/bin/env python3
"""
AIML Actions Engine - Hybrid AIML + LLM Pattern Matcher

A conversational pattern matching engine that combines AIML's deterministic
pattern matching with LLM fallback for novel situations. Designed for
"Choose Your Own Adventure" style DevOps orchestration.
"""

import re
import json
import os
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import random


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ActionResult:
    """Result of an AIML action execution"""
    text: str
    action: Optional[str] = None
    workflow: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    choices: Optional[List[Dict[str, str]]] = None
    confirm: Optional[str] = None
    learn: Optional[Dict[str, str]] = None


@dataclass
class Category:
    """An AIML category (pattern-template pair)"""
    pattern: str
    template: str
    that: Optional[str] = None
    topic: Optional[str] = None


@dataclass
class PatternMatch:
    """Result of pattern matching"""
    matched: bool
    stars: List[str] = field(default_factory=list)
    category: Optional[Category] = None


# ═══════════════════════════════════════════════════════════════════════════════
# AIML ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AIMLEngine:
    """
    AIML Pattern Matching Engine with GitHub Actions integration.
    
    Supports standard AIML tags plus custom extensions:
    - <action> - Trigger GitHub Actions workflow
    - <choice> - Present branching options
    - <confirm> - Require user confirmation
    - <llm> - Invoke LLM for dynamic content
    - <learn-action> - Learn new pattern
    """
    
    def __init__(self, patterns_dir: Optional[str] = None):
        self.categories: List[Category] = []
        self.variables: Dict[str, str] = {}
        self.topic: str = "*"
        self.that: str = ""
        self.history: List[Tuple[str, str]] = []
        
        # Load patterns if directory provided
        if patterns_dir:
            self.load_patterns(patterns_dir)
    
    def load_patterns(self, patterns_dir: str):
        """Load all AIML files from a directory"""
        path = Path(patterns_dir)
        if not path.exists():
            return
        
        for aiml_file in path.glob("*.aiml"):
            self.load_file(str(aiml_file))
    
    def load_file(self, filepath: str):
        """Load categories from an AIML file"""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            current_topic = "*"
            
            for element in root:
                if element.tag == "topic":
                    current_topic = element.get("name", "*")
                    for category in element.findall("category"):
                        self._parse_category(category, current_topic)
                elif element.tag == "category":
                    self._parse_category(element, current_topic)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    def _parse_category(self, element: ET.Element, topic: str = "*"):
        """Parse a category element"""
        pattern_elem = element.find("pattern")
        template_elem = element.find("template")
        that_elem = element.find("that")
        
        if pattern_elem is not None and template_elem is not None:
            pattern = self._get_text(pattern_elem).upper().strip()
            template = ET.tostring(template_elem, encoding="unicode", method="xml")
            that = self._get_text(that_elem).upper().strip() if that_elem is not None else None
            
            self.categories.append(Category(
                pattern=pattern,
                template=template,
                that=that,
                topic=topic
            ))
    
    def _get_text(self, element: ET.Element) -> str:
        """Get text content from an element"""
        if element is None:
            return ""
        return "".join(element.itertext())
    
    def respond(self, input_text: str) -> Optional[ActionResult]:
        """
        Process input and return a response.
        
        Returns None if no pattern matches (triggers LLM fallback).
        """
        normalized = self._normalize(input_text)
        
        # Try to find a matching pattern
        match = self._match_pattern(normalized)
        
        if not match.matched:
            return None
        
        # Process the template
        result = self._process_template(match.category.template, match.stars)
        
        # Update history
        self.that = result.text.upper() if result.text else ""
        self.history.append((input_text, result.text))
        
        return result
    
    def _normalize(self, text: str) -> str:
        """Normalize input text for pattern matching"""
        # Convert to uppercase
        text = text.upper()
        # Remove punctuation except wildcards
        text = re.sub(r'[^\w\s*_#^]', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def _match_pattern(self, input_text: str) -> PatternMatch:
        """Find the best matching pattern"""
        best_match = PatternMatch(matched=False)
        best_score = -1
        
        for category in self.categories:
            # Check topic
            if category.topic != "*" and category.topic != self.topic:
                continue
            
            # Check that (previous response context)
            if category.that and category.that != self.that:
                continue
            
            # Try to match pattern
            stars, score = self._pattern_match(category.pattern, input_text)
            
            if stars is not None and score > best_score:
                best_score = score
                best_match = PatternMatch(
                    matched=True,
                    stars=stars,
                    category=category
                )
        
        return best_match
    
    def _pattern_match(self, pattern: str, input_text: str) -> Tuple[Optional[List[str]], int]:
        """
        Match input against pattern, returning captured wildcards and score.
        
        Wildcards:
        - * : One or more words
        - _ : One or more words (higher priority)
        - # : Zero or more words
        - ^ : Zero or more words (highest priority)
        """
        # Convert AIML pattern to regex
        regex_parts = []
        score = 0
        
        for part in pattern.split():
            if part == "*":
                regex_parts.append(r"(.+?)")
                score += 1
            elif part == "_":
                regex_parts.append(r"(.+?)")
                score += 2
            elif part == "#":
                regex_parts.append(r"(.*?)")
                score += 1
            elif part == "^":
                regex_parts.append(r"(.*?)")
                score += 3
            else:
                regex_parts.append(re.escape(part))
                score += 10  # Exact matches score higher
        
        regex = r"^\s*" + r"\s+".join(regex_parts) + r"\s*$"
        
        try:
            match = re.match(regex, input_text, re.IGNORECASE)
            if match:
                return list(match.groups()), score
        except re.error:
            pass
        
        return None, 0
    
    def _process_template(self, template: str, stars: List[str]) -> ActionResult:
        """Process a template and return the result"""
        result = ActionResult(text="")
        
        try:
            # Parse template XML
            root = ET.fromstring(template)
            result.text = self._process_element(root, stars, result)
        except ET.ParseError:
            # If not valid XML, treat as plain text
            result.text = template
        
        return result
    
    def _process_element(self, element: ET.Element, stars: List[str], result: ActionResult) -> str:
        """Process a template element recursively"""
        output = []
        
        # Process element text
        if element.text:
            output.append(element.text)
        
        # Process child elements
        for child in element:
            tag = child.tag.lower()
            
            if tag == "star":
                # Wildcard substitution
                index = int(child.get("index", "1")) - 1
                if 0 <= index < len(stars):
                    output.append(stars[index])
            
            elif tag == "get":
                # Variable retrieval
                name = child.get("name", "")
                output.append(self.variables.get(name, ""))
            
            elif tag == "set":
                # Variable assignment
                name = child.get("name", "")
                value = self._process_element(child, stars, result)
                self.variables[name] = value
                output.append(value)
            
            elif tag == "think":
                # Silent processing
                self._process_element(child, stars, result)
            
            elif tag == "random":
                # Random selection
                items = child.findall("li")
                if items:
                    chosen = random.choice(items)
                    output.append(self._process_element(chosen, stars, result))
            
            elif tag == "condition":
                # Conditional logic
                name = child.get("name")
                value = child.get("value")
                
                if name and value:
                    if self.variables.get(name) == value:
                        output.append(self._process_element(child, stars, result))
                else:
                    # Multi-condition
                    for li in child.findall("li"):
                        li_name = li.get("name", name)
                        li_value = li.get("value")
                        if li_value is None or self.variables.get(li_name) == li_value:
                            output.append(self._process_element(li, stars, result))
                            break
            
            elif tag == "srai":
                # Symbolic reduction (recursive call)
                redirect = self._process_element(child, stars, result)
                sub_result = self.respond(redirect)
                if sub_result:
                    output.append(sub_result.text)
            
            elif tag == "uppercase":
                output.append(self._process_element(child, stars, result).upper())
            
            elif tag == "lowercase":
                output.append(self._process_element(child, stars, result).lower())
            
            elif tag == "formal":
                output.append(self._process_element(child, stars, result).title())
            
            # ═══════════════════════════════════════════════════════════════
            # CUSTOM EXTENSIONS FOR AIML ACTIONS
            # ═══════════════════════════════════════════════════════════════
            
            elif tag == "action":
                # GitHub Actions workflow trigger
                workflow = child.get("workflow")
                inputs_str = child.get("inputs", "{}")
                
                # Process any star references in inputs
                for i, star in enumerate(stars):
                    inputs_str = inputs_str.replace(f'<star index="{i+1}"/>', star)
                    inputs_str = inputs_str.replace(f'<star/>', stars[0] if stars else "")
                
                try:
                    inputs = json.loads(inputs_str)
                except json.JSONDecodeError:
                    inputs = {}
                
                result.action = "workflow"
                result.workflow = workflow
                result.inputs = inputs
                
                output.append(self._process_element(child, stars, result))
            
            elif tag == "choice":
                # Branching options
                choice_id = child.get("id", "choice")
                options = []
                
                for option in child.findall("option"):
                    options.append({
                        "value": option.get("value", ""),
                        "label": self._get_text(option)
                    })
                
                if not options:
                    # Parse pipe-separated options
                    text = self._get_text(child)
                    for opt in text.split("|"):
                        opt = opt.strip()
                        if opt:
                            options.append({"value": opt.lower(), "label": opt})
                
                result.choices = options
                output.append(self._process_element(child, stars, result))
            
            elif tag == "confirm":
                # Confirmation required
                result.confirm = self._process_element(child, stars, result)
                result.action = "confirm"
            
            elif tag == "llm":
                # LLM invocation (placeholder - handled by fallback)
                result.action = "llm"
                prompt = self._process_element(child, stars, result)
                output.append(f"[LLM: {prompt}]")
            
            elif tag == "learn-action":
                # Learn new pattern
                new_pattern = child.get("pattern", "")
                new_workflow = child.get("workflow", "")
                
                # Process star references
                for i, star in enumerate(stars):
                    new_pattern = new_pattern.replace(f"<star index=\"{i+1}\"/>", "*")
                
                result.learn = {
                    "pattern": new_pattern,
                    "workflow": new_workflow
                }
                result.action = "learn"
            
            elif tag == "compute":
                # Simple arithmetic
                expr = self._process_element(child, stars, result)
                try:
                    # Safe eval for simple math
                    computed = eval(expr, {"__builtins__": {}}, {})
                    output.append(str(computed))
                except:
                    output.append(expr)
            
            else:
                # Unknown tag - process children
                output.append(self._process_element(child, stars, result))
            
            # Process tail text
            if child.tail:
                output.append(child.tail)
        
        return "".join(output).strip()
    
    def set_topic(self, topic: str):
        """Set the current conversation topic"""
        self.topic = topic.upper()
    
    def set_variable(self, name: str, value: str):
        """Set a bot variable"""
        self.variables[name] = value
    
    def get_variable(self, name: str) -> str:
        """Get a bot variable"""
        return self.variables.get(name, "")
    
    def add_category(self, pattern: str, template: str, topic: str = "*"):
        """Dynamically add a new category"""
        self.categories.append(Category(
            pattern=pattern.upper(),
            template=f"<template>{template}</template>",
            topic=topic.upper() if topic != "*" else "*"
        ))
    
    def save_learned_patterns(self, filepath: str):
        """Save dynamically learned patterns to an AIML file"""
        root = ET.Element("aiml", version="2.0")
        
        for category in self.categories:
            if hasattr(category, "_learned") and category._learned:
                cat_elem = ET.SubElement(root, "category")
                
                pattern_elem = ET.SubElement(cat_elem, "pattern")
                pattern_elem.text = category.pattern
                
                template_elem = ET.SubElement(cat_elem, "template")
                template_elem.text = category.template
        
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding="unicode", xml_declaration=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

class LLMFallback:
    """
    LLM fallback for when no AIML pattern matches.
    
    Uses local llama.cpp server first, falls back to cloud APIs.
    """
    
    def __init__(self):
        self.local_url = os.environ.get("LLAMA_URL", "http://localhost:8080/v1/chat/completions")
        self.cloud_url = os.environ.get("OPENAI_URL", "https://api.openai.com/v1/chat/completions")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # Known intents for pattern suggestion
        self.known_intents = {
            "create": ["create", "make", "new", "add", "spin up"],
            "delete": ["delete", "remove", "destroy", "tear down"],
            "list": ["list", "show", "get", "display", "view"],
            "update": ["update", "modify", "change", "edit"],
            "sync": ["sync", "synchronize", "mirror", "replicate"],
            "deploy": ["deploy", "release", "ship", "publish"],
        }
    
    def handle(self, input_text: str, context: Dict[str, Any] = None) -> ActionResult:
        """Handle unmatched input with LLM"""
        # Try to classify intent
        intent = self._classify_intent(input_text)
        
        if intent:
            # Suggest a pattern for learning
            pattern = self._suggest_pattern(input_text, intent)
            return ActionResult(
                text=f"I don't have a pattern for that yet, but I can learn!\n\n"
                     f"Suggested pattern: `{pattern}`\n\n"
                     f"Should I add this to my knowledge?",
                action="suggest_learn",
                learn={"pattern": pattern, "intent": intent}
            )
        
        # Generate response with LLM
        return self._generate_response(input_text, context)
    
    def _classify_intent(self, input_text: str) -> Optional[str]:
        """Classify the intent of the input"""
        lower = input_text.lower()
        
        for intent, keywords in self.known_intents.items():
            for keyword in keywords:
                if keyword in lower:
                    return intent
        
        return None
    
    def _suggest_pattern(self, input_text: str, intent: str) -> str:
        """Suggest an AIML pattern based on input"""
        # Simple pattern generalization
        words = input_text.upper().split()
        pattern_words = []
        
        for word in words:
            # Keep intent keywords, replace specifics with wildcards
            if word.lower() in self.known_intents.get(intent, []):
                pattern_words.append(word)
            elif word.isdigit():
                pattern_words.append("*")
            elif len(word) > 3:
                pattern_words.append("*")
            else:
                pattern_words.append(word)
        
        # Collapse consecutive wildcards
        result = []
        prev_wildcard = False
        for word in pattern_words:
            if word == "*":
                if not prev_wildcard:
                    result.append("*")
                prev_wildcard = True
            else:
                result.append(word)
                prev_wildcard = False
        
        return " ".join(result)
    
    def _generate_response(self, input_text: str, context: Dict[str, Any] = None) -> ActionResult:
        """Generate a response using LLM"""
        import requests
        
        system_prompt = """You are GodChat, an AI assistant for DevOps and infrastructure management.
You help users manage Azure AD, GitHub, and cloud infrastructure.
When users ask about operations you can't perform directly, suggest the appropriate command or workflow.
Be concise and helpful."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ]
        
        # Try local LLM first
        try:
            response = requests.post(
                self.local_url,
                json={
                    "model": "local",
                    "messages": messages,
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                return ActionResult(text=text)
        except:
            pass
        
        # Fall back to cloud API
        if self.api_key:
            try:
                response = requests.post(
                    self.cloud_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.7
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    return ActionResult(text=text)
            except:
                pass
        
        # Ultimate fallback
        return ActionResult(
            text="I'm not sure how to help with that. Could you rephrase or try a specific command like:\n"
                 "- `create user <name>`\n"
                 "- `list repos`\n"
                 "- `deploy to staging`"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AIMLActionsEngine:
    """
    Combined AIML + LLM engine for AIML Actions.
    
    Provides a unified interface for pattern matching with LLM fallback.
    """
    
    def __init__(self, patterns_dir: Optional[str] = None):
        self.aiml = AIMLEngine(patterns_dir)
        self.llm = LLMFallback()
        self.pending_learn: Optional[Dict[str, str]] = None
    
    def respond(self, input_text: str) -> ActionResult:
        """Process input and return response"""
        # Check for learning confirmation
        if self.pending_learn:
            if input_text.lower() in ["yes", "y", "sure", "ok", "learn"]:
                pattern = self.pending_learn["pattern"]
                self.aiml.add_category(pattern, f"Executing {pattern}...")
                self.pending_learn = None
                return ActionResult(text=f"Learned! I'll remember `{pattern}` for next time.")
            else:
                self.pending_learn = None
                return ActionResult(text="No problem, I won't learn that pattern.")
        
        # Try AIML first
        result = self.aiml.respond(input_text)
        
        if result:
            return result
        
        # Fall back to LLM
        result = self.llm.handle(input_text)
        
        # Track pending learn suggestions
        if result.action == "suggest_learn" and result.learn:
            self.pending_learn = result.learn
        
        return result
    
    def set_topic(self, topic: str):
        """Set conversation topic"""
        self.aiml.set_topic(topic)
    
    def load_patterns(self, patterns_dir: str):
        """Load additional patterns"""
        self.aiml.load_patterns(patterns_dir)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Simple CLI for testing the AIML Actions engine"""
    import sys
    
    # Initialize engine
    patterns_dir = os.path.join(os.path.dirname(__file__), "..", "patterns")
    engine = AIMLActionsEngine(patterns_dir)
    
    print("AIML Actions Engine")
    print("Type 'quit' to exit, 'topic <name>' to set topic")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                break
            
            if user_input.lower().startswith("topic "):
                topic = user_input[6:].strip()
                engine.set_topic(topic)
                print(f"Topic set to: {topic}")
                continue
            
            result = engine.respond(user_input)
            
            print(f"\nBot: {result.text}")
            
            if result.action == "workflow":
                print(f"\n[ACTION] Trigger workflow: {result.workflow}")
                print(f"[INPUTS] {json.dumps(result.inputs, indent=2)}")
            
            if result.choices:
                print("\nChoices:")
                for i, choice in enumerate(result.choices, 1):
                    print(f"  [{i}] {choice['label']}")
            
            if result.confirm:
                print(f"\n[CONFIRM] {result.confirm}")
        
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()
