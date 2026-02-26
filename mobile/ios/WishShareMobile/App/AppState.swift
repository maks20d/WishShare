import Combine
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()

    @Published var path: [QuickActionType] = []
    @Published var shortcutsEnabled: Bool {
        didSet {
            QuickActionStore.shared.setShortcutsEnabled(shortcutsEnabled)
            QuickActionManager.shared.applyShortcuts()
        }
    }
    @Published var shortcuts: [ShortcutConfig] {
        didSet {
            QuickActionStore.shared.save(shortcuts)
            QuickActionManager.shared.applyShortcuts()
        }
    }

    init() {
        self.shortcutsEnabled = QuickActionStore.shared.isShortcutsEnabled()
        self.shortcuts = QuickActionStore.shared.loadShortcuts()
        QuickActionManager.shared.setAppState(self)
        QuickActionManager.shared.applyShortcuts()
    }

    func handleQuickAction(_ action: QuickActionType) {
        path = [action]
    }

    func addShortcut() {
        shortcuts.append(ShortcutConfig.defaultConfig())
    }

    func removeShortcut(_ config: ShortcutConfig) {
        shortcuts.removeAll { $0.id == config.id }
    }

    func updateShortcut(_ config: ShortcutConfig) {
        guard let index = shortcuts.firstIndex(where: { $0.id == config.id }) else { return }
        shortcuts[index] = config
    }
}

