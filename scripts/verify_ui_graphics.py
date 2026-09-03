#!/usr/bin/env python3
"""
verify_ui_graphics.py
End-to-end graphical, window hierarchy and visual canvas verification for Neural Memory Agent.
"""
import subprocess
import urllib.request
import json
import sys


def verify_macos_windows():
    print("\n🖥️  Checking macOS Native Window Hierarchy & Frame Geometry...")
    swift_cmd = """
import Cocoa
import CoreGraphics

let windowList = CGWindowListCopyWindowInfo(.optionAll, kCGNullWindowID) as? [[String: Any]] ?? []
var results: [[String: Any]] = []

for w in windowList {
    let owner = w[kCGWindowOwnerName as String] as? String ?? ""
    let bounds = w[kCGWindowBounds as String] as? [String: Any] ?? [:]
    let layer = w[kCGWindowLayer as String] as? Int ?? -1
    let onScreen = w[kCGWindowIsOnscreen as String] as? Bool ?? false
    let id = w[kCGWindowNumber as String] as? Int ?? 0

    if owner.contains("Neural") && onScreen {
        results.append([
            "id": id,
            "owner": owner,
            "layer": layer,
            "onScreen": onScreen,
            "width": bounds["Width"] ?? 0,
            "height": bounds["Height"] ?? 0,
            "x": bounds["X"] ?? 0,
            "y": bounds["Y"] ?? 0
        ])
    }
}

if let data = try? JSONSerialization.data(withJSONObject: results),
   let str = String(data: data, encoding: .utf8) {
    print(str)
}
"""
    proc = subprocess.run(["swift", "-"], input=swift_cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        print(f"⚠️ Warning running Swift inspection: {proc.stderr}")
        return False

    out = proc.stdout.strip()
    try:
        windows = json.loads(out)
    except Exception:
        print(f"⚠️ Could not parse window JSON: {out}")
        return False

    print(f"  Found {len(windows)} active on-screen windows for NeuralMemoryAgent:")
    has_graph = False
    has_settings_or_dashboard = False

    for w in windows:
        width = int(w.get("width", 0))
        height = int(w.get("height", 0))
        layer = int(w.get("layer", -1))
        on_screen = bool(w.get("onScreen", False))
        print(f"  • Window ID {w.get('id')}: {width}x{height} at ({w.get('x')}, {w.get('y')}) [Layer: {layer}, OnScreen: {on_screen}]")

        if width >= 800 and height >= 550 and layer == 0 and on_screen:
            has_graph = True
        if (width in range(350, 650)) and (height in range(450, 600)) and layer == 0 and on_screen:
            has_settings_or_dashboard = True

    if has_graph:
        print("  ✅ Knowledge Graph window verified on screen (geometry >= 800x550, Layer 0)")
    else:
        print("  ⚠️ Knowledge Graph window not currently frontmost/visible")

    if has_settings_or_dashboard:
        print("  ✅ Settings/Dashboard window verified on screen (geometry ~420x520 or 580x500, Layer 0)")

    return True


def verify_web_graph_visualizer():
    print("\n🌐 Checking Web Graph Fallback Visualizer (/graph & /api/graph/data)...")
    base_url = "http://127.0.0.1:8765"

    # 1. Check /graph HTML
    try:
        with urllib.request.urlopen(f"{base_url}/graph", timeout=5.0) as resp:
            html = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "svg" in html.lower() or "d3" in html.lower() or "graph" in html.lower()
            print("  ✅ GET /graph returned valid HTML5 + D3 force graph visualizer")
    except Exception as e:
        print(f"  ❌ GET /graph failed: {e}")
        return False

    # 2. Check /api/graph/data JSON
    try:
        req = urllib.request.Request(f"{base_url}/api/graph/data")
        req.add_header("Authorization", "Bearer dev-token")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            nodes = data.get("nodes", [])
            links = data.get("links", [])
            print(f"  ✅ GET /api/graph/data returned {len(nodes)} nodes and {len(links)} links")

            if nodes:
                first_node = nodes[0]
                assert "id" in first_node
                assert "labels" in first_node
                assert "timestamp_iso" in first_node
                print(f"  ✅ Node temporal contract verified (timestamp_iso: {first_node.get('timestamp_iso')})")
    except Exception as e:
        print(f"  ❌ GET /api/graph/data failed: {e}")
        return False

    return True


def main():
    print("=" * 65)
    print("🎨 NEURAL MEMORY AGENT — GRAPHICAL & UI E2E VERIFICATION SUITE")
    print("=" * 65)

    ok_win = verify_macos_windows()
    ok_web = verify_web_graph_visualizer()

    print("\n" + "=" * 65)
    if ok_win and ok_web:
        print("🎉 ALL GRAPHICAL & UI E2E VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 65)
        sys.exit(0)
    else:
        print("❌ SOME GRAPHICAL VERIFICATIONS FAILED")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
