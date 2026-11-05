"""Validate a small YAML domain model for terms, transitions, and invariants."""

import argparse
import json
from pathlib import Path
import sys

import yaml


def validate_model(data):
    errors = []
    if not isinstance(data, dict):
        return ["model must be a mapping"]
    for key in ("model", "terms", "states", "initial", "transitions", "events", "invariants"):
        if key not in data:
            errors.append("missing key: {}".format(key))
    if errors:
        return errors
    terms = data["terms"]
    states = data["states"]
    if not isinstance(terms, list) or not terms:
        errors.append("terms must be a nonempty list")
    else:
        names = []
        for index, item in enumerate(terms):
            if not isinstance(item, dict) or not item.get("term") or not item.get("definition"):
                errors.append("term {} needs term and definition".format(index))
                continue
            if item["term"] in names:
                errors.append("duplicate term: {}".format(item["term"]))
            names.append(item["term"])
    if not isinstance(states, list) or not states or not all(isinstance(state, str) and state for state in states):
        errors.append("states must be a nonempty string list")
        states = []
    if len(set(states)) != len(states):
        errors.append("states contain duplicates")
    if data["initial"] not in states:
        errors.append("initial state is not declared")
    transitions = data["transitions"]
    if not isinstance(transitions, list) or not transitions:
        errors.append("transitions must be a nonempty list")
        transitions = []
    events = data["events"]
    if not isinstance(events, list) or not events:
        errors.append("events must be a nonempty list")
        events = []
    event_names = set()
    for event in events:
        if not isinstance(event, dict) or not event.get("name"):
            errors.append("event needs a name")
        elif event["name"] in event_names:
            errors.append("duplicate event: {}".format(event["name"]))
        else:
            event_names.add(event["name"])
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            errors.append("transition {} must be a mapping".format(index))
            continue
        for key in ("from", "to", "event"):
            if not transition.get(key):
                errors.append("transition {} needs {}".format(index, key))
        if transition.get("from") not in states or transition.get("to") not in states:
            errors.append("transition {} references an unknown state".format(index))
        if transition.get("event") not in event_names:
            errors.append("transition {} references an unknown event".format(index))
    invariants = data["invariants"]
    if not isinstance(invariants, list) or not invariants:
        errors.append("invariants must be a nonempty list")
    else:
        ids = set()
        for invariant in invariants:
            if not isinstance(invariant, dict) or not invariant.get("id") or not invariant.get("statement"):
                errors.append("invariant needs id and statement")
            elif invariant["id"] in ids:
                errors.append("duplicate invariant: {}".format(invariant["id"]))
            else:
                ids.add(invariant["id"])
    return errors


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        errors = validate_model(load(args.path))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        print("invalid model: {}".format(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2, ensure_ascii=False))
    elif errors:
        for error in errors:
            print("FAIL " + error)
    else:
        print("Domain model is valid.")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
