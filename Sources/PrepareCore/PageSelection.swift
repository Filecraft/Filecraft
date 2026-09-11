import Foundation

public enum PageBatchAction: CaseIterable, Sendable {
    case sortByFilename, reverse, rotateAll, clear
}

public struct PageEntry: Identifiable, Sendable, Equatable {
    public let id: UUID
    public let url: URL
    public var rotation: PageRotation = .none
    public init(url: URL) { self.id = UUID(); self.url = url }
    public var page: PreparationPage { PreparationPage(url: url, rotation: rotation) }
}

public struct PageSelection: Sendable {
    public private(set) var entries: [PageEntry]
    public private(set) var selectedID: UUID?
    public init(entries: [PageEntry] = []) { self.entries = entries; selectedID = entries.first?.id }
    public var selectedIndex: Int? { entries.firstIndex { $0.id == selectedID } }
    public var selected: PageEntry? { selectedIndex.map { entries[$0] } }
    @discardableResult
    public mutating func moveSelectedLast(isBusy: Bool = false) -> Bool {
        guard !isBusy, let index = selectedIndex, index < entries.count - 1 else { return false }
        entries.append(entries.remove(at: index))
        return true
    }
    @discardableResult
    public mutating func duplicateSelected(isBusy: Bool = false) -> Bool {
        guard !isBusy, entries.count < 20, let index = selectedIndex else { return false }
        var copy = PageEntry(url: entries[index].url)
        copy.rotation = entries[index].rotation
        entries.insert(copy, at: index + 1)
        selectedID = copy.id
        return true
    }
    /// Returns false for guarded or unchanged edits so a reviewed result stays valid.
    @discardableResult
    public mutating func apply(_ action: PageBatchAction, isBusy: Bool = false) -> Bool {
        guard !isBusy, !entries.isEmpty else { return false }
        let previous = entries
        switch action {
        case .sortByFilename:
            entries = entries.enumerated().sorted { lhs, rhs in
                let order = lhs.element.url.lastPathComponent.localizedStandardCompare(rhs.element.url.lastPathComponent)
                return order == .orderedSame ? lhs.offset < rhs.offset : order == .orderedAscending
            }.map(\.element)
        case .reverse: entries.reverse()
        case .rotateAll:
            for index in entries.indices { entries[index].rotation = entries[index].rotation.next }
        case .clear: entries.removeAll(); selectedID = nil
        }
        return entries != previous
    }
    public mutating func select(_ id: UUID) {
        guard entries.contains(where: { $0.id == id }) else { return }
        selectedID = id
    }
    public mutating func move(_ id: UUID, to target: UUID) {
        guard let from = entries.firstIndex(where: { $0.id == id }),
              let to = entries.firstIndex(where: { $0.id == target }) else { return }
        entries = PageOrder.moving(entries, from: from, to: to)
    }
    public mutating func rotateSelected() {
        guard let index = selectedIndex else { return }
        entries[index].rotation = entries[index].rotation.next
    }
    public mutating func remove(_ id: UUID) {
        guard let index = entries.firstIndex(where: { $0.id == id }) else { return }
        entries.remove(at: index)
        if selectedID == id { selectedID = entries.isEmpty ? nil : entries[min(index, entries.count - 1)].id }
    }
    public mutating func step(_ offset: Int) {
        guard let index = selectedIndex else { return }
        // Clamp the delta before adding so even an arbitrary caller cannot overflow.
        let delta = min(entries.count, max(-entries.count, offset))
        selectedID = entries[min(entries.count - 1, max(0, index + delta))].id
    }
}
