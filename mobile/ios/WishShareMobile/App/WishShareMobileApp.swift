import SwiftUI

@main
struct WishShareMobileApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState.shared
    
    var body: some Scene {
        WindowGroup {
            MainView()
                .environmentObject(appState)
                .onOpenURL { url in
                    if let action = QuickActionType(from: url) {
                        appState.handleQuickAction(action)
                    }
                }
        }
    }
}
