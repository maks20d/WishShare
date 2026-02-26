import SwiftUI

struct MainView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        NavigationStack(path: $appState.path) {
            List {
                Section {
                    NavigationLink(value: QuickActionType.openMain) {
                        Label(NSLocalizedString("feature.main", comment: ""), systemImage: "sparkles")
                    }
                    NavigationLink(value: QuickActionType.openCreate) {
                        Label(NSLocalizedString("feature.create", comment: ""), systemImage: "plus.circle")
                    }
                    NavigationLink(value: QuickActionType.openScanner) {
                        Label(NSLocalizedString("feature.scanner", comment: ""), systemImage: "qrcode.viewfinder")
                    }
                    NavigationLink(value: QuickActionType.openDashboard) {
                        Label(NSLocalizedString("feature.dashboard", comment: ""), systemImage: "list.bullet.rectangle")
                    }
                } header: {
                    Text(NSLocalizedString("section.features", comment: ""))
                }

                Section {
                    NavigationLink {
                        SettingsView()
                    } label: {
                        Label(NSLocalizedString("section.shortcuts", comment: ""), systemImage: "bolt.fill")
                    }
                }
            }
            .navigationTitle(NSLocalizedString("app.title", comment: ""))
            .navigationDestination(for: QuickActionType.self) { action in
                FeatureView(action: action)
            }
        }
    }
}

