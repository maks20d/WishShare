import UIKit
import SwiftUI

final class QuickActionManager {
    static let shared = QuickActionManager()
    private weak var appState: AppState?

    func setAppState(_ state: AppState) {
        self.appState = state
    }

    func bootstrap() {
        applyShortcuts()
    }

    func applyShortcuts() {
        guard let state = appState ?? AppState.shared else { return }
        let items: [UIApplicationShortcutItem]
        if state.shortcutsEnabled {
            let active = state.shortcuts.filter { $0.enabled }.prefix(4)
            items = active.map { cfg in
                let icon = UIApplicationShortcutIcon(systemImageName: cfg.icon)
                return UIApplicationShortcutItem(type: "wishshare.\(cfg.action.rawValue)",
                                                 localizedTitle: cfg.title,
                                                 localizedSubtitle: nil,
                                                 icon: icon,
                                                 userInfo: ["action": cfg.action.rawValue] as [String: NSSecureCoding])
            }
        } else {
            items = []
        }
        DispatchQueue.main.async {
            UIApplication.shared.shortcutItems = items
        }
    }

    @discardableResult
    func handle(shortcutItem: UIApplicationShortcutItem) -> Bool {
        let actionRaw = (shortcutItem.userInfo?["action"] as? String) ?? shortcutItem.type.split(separator: ".").last.map(String.init) ?? ""
        guard let action = QuickActionType(rawValue: actionRaw) else { return false }
        DispatchQueue.main.async {
            (self.appState ?? AppState.shared).handleQuickAction(action)
        }
        return true
    }
}
