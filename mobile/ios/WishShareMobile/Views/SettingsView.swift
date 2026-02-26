import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var editing: ShortcutConfig?

    var body: some View {
        List {
            Section {
                Toggle(NSLocalizedString("settings.shortcuts_enabled", comment: ""), isOn: $appState.shortcutsEnabled)
            }

            Section(NSLocalizedString("settings.shortcuts", comment: "")) {
                ForEach(appState.shortcuts) { item in
                    Button {
                        editing = item
                    } label: {
                        HStack {
                            Image(systemName: item.icon)
                                .frame(width: 22)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(item.title)
                                Text(actionTitle(item.action)).font(.caption).foregroundColor(.secondary)
                            }
                            Spacer()
                            Toggle("", isOn: Binding(
                                get: { item.enabled },
                                set: { newValue in
                                    var updated = item; updated.enabled = newValue
                                    appState.updateShortcut(updated)
                                }
                            ))
                            .labelsHidden()
                        }
                    }
                }
                .onDelete { idxSet in
                    idxSet.compactMap { appState.shortcuts[$0] }.forEach(appState.removeShortcut)
                }

                Button {
                    appState.addShortcut()
                } label: {
                    Label(NSLocalizedString("settings.add_shortcut", comment: ""), systemImage: "plus")
                }
            }
        }
        .navigationTitle(NSLocalizedString("settings.title", comment: ""))
        .sheet(item: $editing) { item in
            EditShortcutSheet(config: item) { updated in
                appState.updateShortcut(updated)
            }
        }
    }
}

private struct EditShortcutSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State var config: ShortcutConfig
    var onSave: (ShortcutConfig) -> Void

    private let availableIcons = [
        "star.fill", "plus.circle.fill", "qrcode.viewfinder",
        "list.bullet.rectangle", "gift.fill", "heart.fill", "paperplane.fill"
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section(NSLocalizedString("settings.shortcut_title", comment: "")) {
                    TextField(NSLocalizedString("settings.title_placeholder", comment: ""), text: $config.title)
                }
                Section(NSLocalizedString("settings.shortcut_action", comment: "")) {
                    Picker(NSLocalizedString("settings.shortcut_action", comment: ""), selection: $config.action) {
                        ForEach(QuickActionType.allCases) { t in
                            Text(t.defaultTitle).tag(t)
                        }
                    }
                }
                Section(NSLocalizedString("settings.shortcut_icon", comment: "")) {
                    LazyVGrid(columns: Array(repeating: .init(.flexible(), spacing: 12), count: 4), spacing: 12) {
                        ForEach(availableIcons, id: \.self) { name in
                            Button {
                                config.icon = name
                            } label: {
                                Image(systemName: name)
                                    .font(.system(size: 24))
                                    .frame(maxWidth: .infinity, minHeight: 44)
                                    .background(config.icon == name ? Color.accentColor.opacity(0.15) : .clear)
                                    .clipShape(RoundedRectangle(cornerRadius: 8))
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle(NSLocalizedString("settings.edit_shortcut", comment: ""))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(NSLocalizedString("common.cancel", comment: "")) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(NSLocalizedString("common.save", comment: "")) {
                        onSave(config); dismiss()
                    }
                    .disabled(config.title.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}

private func actionTitle(_ action: QuickActionType) -> String {
    action.defaultTitle
}
