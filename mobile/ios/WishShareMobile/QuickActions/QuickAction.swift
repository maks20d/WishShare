import UIKit

enum QuickActionType: String, CaseIterable, Codable, Identifiable {
    case openMain
    case openCreate
    case openScanner
    case openDashboard

    var id: String { rawValue }

    var systemImageName: String {
        switch self {
        case .openMain: return "star.fill"
        case .openCreate: return "plus.circle.fill"
        case .openScanner: return "qrcode.viewfinder"
        case .openDashboard: return "list.bullet.rectangle"
        }
    }

    var defaultTitle: String {
        switch self {
        case .openMain: return NSLocalizedString("shortcut.open_main", comment: "Open main")
        case .openCreate: return NSLocalizedString("shortcut.open_create", comment: "Open create")
        case .openScanner: return NSLocalizedString("shortcut.open_scanner", comment: "Open scanner")
        case .openDashboard: return NSLocalizedString("shortcut.open_dashboard", comment: "Open dashboard")
        }
    }

    init?(from url: URL) {
        guard url.scheme == "wishshare", url.host == "shortcut",
              let item = url.pathComponents.dropFirst().first,
              let type = QuickActionType(rawValue: item) else { return nil }
        self = type
    }
}

struct ShortcutConfig: Codable, Identifiable, Hashable {
    var id: UUID
    var enabled: Bool
    var title: String
    var icon: String
    var action: QuickActionType

    static func `defaultConfig`() -> ShortcutConfig {
        .init(id: UUID(), enabled: true, title: QuickActionType.openMain.defaultTitle,
              icon: QuickActionType.openMain.systemImageName, action: .openMain)
    }
}

final class QuickActionStore {
    static let shared = QuickActionStore()
    private let keyEnabled = "ws.shortcuts.enabled"
    private let keyItems = "ws.shortcuts.items"
    private let defaults = UserDefaults.standard

    func isShortcutsEnabled() -> Bool {
        defaults.object(forKey: keyEnabled) as? Bool ?? true
    }
    func setShortcutsEnabled(_ enabled: Bool) {
        defaults.set(enabled, forKey: keyEnabled)
    }
    func loadShortcuts() -> [ShortcutConfig] {
        guard let data = defaults.data(forKey: keyItems),
              let items = try? JSONDecoder().decode([ShortcutConfig].self, from: data) else {
            return [
                .init(id: UUID(), enabled: true, title: QuickActionType.openMain.defaultTitle,
                      icon: QuickActionType.openMain.systemImageName, action: .openMain),
                .init(id: UUID(), enabled: true, title: QuickActionType.openCreate.defaultTitle,
                      icon: QuickActionType.openCreate.systemImageName, action: .openCreate)
            ]
        }
        return items
    }
    func save(_ items: [ShortcutConfig]) {
        let data = try? JSONEncoder().encode(items)
        defaults.set(data, forKey: keyItems)
    }
}
