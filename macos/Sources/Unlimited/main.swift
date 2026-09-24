import AppKit
import Combine
import SwiftUI

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let model = StripModel()
    private var item: NSStatusItem!
    private var host: NSHostingView<StripView>!
    private var sizeWatch: Any?
    private let popover = NSPopover()

    func applicationDidFinishLaunching(_ notification: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        host = NSHostingView(rootView: StripView(model: model))
        item.button?.addSubview(host)
        fit()
        // The strip's width follows its tiles.
        sizeWatch = model.objectWillChange.sink { [weak self] _ in
            DispatchQueue.main.async { self?.fit() }
        }
        popover.behavior = .transient
        popover.contentViewController = NSHostingController(rootView: PopoverView(model: model))
        item.button?.target = self
        item.button?.action = #selector(toggle)
        model.start()
    }

    private func fit() {
        let size = host.fittingSize
        host.frame = NSRect(origin: .zero, size: size)
        item.length = size.width
    }

    /// Opens on the account under the pointer.
    @objc private func toggle() {
        if popover.isShown { return popover.performClose(nil) }
        guard let button = item.button, let event = NSApp.currentEvent else { return }
        let x = button.convert(event.locationInWindow, from: nil).x
        let index = Int((x - StripView.padding) / (TileView.width + StripView.spacing))
        model.selected = model.tiles.indices.contains(index) ? model.tiles[index].id : model.tiles.first?.id
        model.refresh(maxAge: 60)
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        popover.contentViewController?.view.window?.makeKey()
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
