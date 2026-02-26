import SwiftUI

struct FeatureView: View {
    let action: QuickActionType

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: action.systemImageName)
                .font(.system(size: 48))
                .foregroundColor(.accentColor)
            Text(title(for: action))
                .font(.title2)
                .fontWeight(.semibold)
            Text(NSLocalizedString("feature.placeholder", comment: ""))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
        }
        .navigationTitle(title(for: action))
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        .background(Color(.systemGroupedBackground))
    }

    private func title(for action: QuickActionType) -> String {
        switch action {
        case .openMain: return NSLocalizedString("feature.main", comment: "")
        case .openCreate: return NSLocalizedString("feature.create", comment: "")
        case .openScanner: return NSLocalizedString("feature.scanner", comment: "")
        case .openDashboard: return NSLocalizedString("feature.dashboard", comment: "")
        }
    }
}

