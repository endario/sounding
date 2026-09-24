import Foundation

/// One account in the menu bar: its label and what its weekly window says.
public struct Tile: Identifiable, Equatable, Sendable {
    public enum Value: Equatable, Sendable {
        case percent(Int)
        case unread      // the vendor refused, or could not be read
        case stale       // the last reading is older than `staleAfter`
        case noWeekly    // the vendor reports no weekly window for this account
        case unknown     // a weekly window whose figure is not known (the moment after a reset)
        case waiting     // nothing read yet

        public var text: String {
            switch self {
            case .percent(let p): "\(p)"
            case .unread, .stale: "!"
            case .noWeekly: "—"
            case .unknown: "?"
            case .waiting: "…"
            }
        }
    }

    public let id: String
    public let label: String
    public let value: Value
    /// A throttled or unusable reading: shown, but not to be trusted as current.
    public let dimmed: Bool

    public static let waiting = Tile(id: "", label: "", value: .waiting, dimmed: false)
    /// The whole strip when `unlimited` cannot be run; the menu says why.
    public static let broken = Tile(id: "", label: "", value: .unread, dimmed: false)
    /// Tunable: a reading older than this says nothing about now.
    public static let staleAfter: TimeInterval = 15 * 60

    static let vendors: [(id: String, code: String)] = [
        ("anthropic", "CL"), ("openai", "CDX"), ("zai", "ZAI"), ("kimi", "KMI"), ("opencode", "OPC"), ("xai", "GRK"),
    ]

    /// Tiles in vendor order, then by label.
    public static func strip(_ readings: [Reading], now: Date) -> [Tile] {
        let order = Dictionary(uniqueKeysWithValues: vendors.enumerated().map { ($1.id, $0) })
        return readings
            .map { tile($0, now: now) }
            .sorted { (order[$0.vendor] ?? .max, $0.tile.label) < (order[$1.vendor] ?? .max, $1.tile.label) }
            .map(\.tile)
    }

    static func tile(_ r: Reading, now: Date) -> (vendor: String, tile: Tile) {
        let throttled = r.retryUntil.map { $0 > now } ?? false
        let stale = r.takenAt.map { now.timeIntervalSince($0) > staleAfter } ?? true
        let value: Value
        if r.status != "ok" {
            value = .unread
        } else if stale && !throttled {
            value = .stale
        } else if let w = r.weekly {
            value = w.usedAtLeast.map { .percent(Int(($0 * 100).rounded())) } ?? .unknown
        } else {
            value = .noWeekly
        }
        let id = "\(r.vendor)/\(r.account ?? "")"
        return (r.vendor, Tile(id: id, label: label(r), value: value, dimmed: throttled || value == .unread || value == .stale))
    }

    /// The vendor's code plus the number in its first identity name: `account2` → CL2,
    /// `claude-glm-2` → ZAI2, `opencode` → OPC. Claude's first directory is `account1`, so CL1.
    static func label(_ r: Reading) -> String {
        let code = vendors.first { $0.id == r.vendor }?.code ?? String(r.vendor.prefix(3)).uppercased()
        let digits = r.names.first.map { String($0.reversed().prefix { $0.isNumber }.reversed()) } ?? ""
        return code + digits
    }
}
