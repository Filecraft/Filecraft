import SwiftUI
import AppKit
import UniformTypeIdentifiers
import PrepareCore

private struct PreviewRequest: Sendable {
    let generation: UUID
    let page: PreparationPage
    let settings: PageSettings
    public let output: Data?
    let index: Int
}

public struct PagePreview: Sendable {
    public let source: Data
    public let output: Data?
}

@MainActor
public final class Workspace: ObservableObject {
    @Published public private(set) var selection = PageSelection()
    @Published public var progress: PreparationProgress?
    @Published public var cancelling = false
    @Published public var megabytes = "2" { didSet { if oldValue != megabytes { invalidate() } } }
    @Published public var profile: CompressionProfile = .balanced { didSet { if oldValue != profile { invalidate() } } }
    @Published public var paper: PaperFormat = .original { didSet { if oldValue != paper { invalidate() } } }
    @Published public var margin = "0" { didSet { if oldValue != margin { invalidate() } } }
    @Published public var result: Prepared?
    @Published public var busy = false
    @Published public var message = ""
    @Published public var reviewed = false
    @Published public private(set) var preview: PagePreview?
    @Published public private(set) var previewLoading = false
    @Published public private(set) var previewError = ""
    private var task: Task<Void, Never>?
    private var worker: Task<Prepared, Error>?
    private var generation = UUID()
    // One active decode and one replaceable pending request: rapid edits never
    // create an unbounded queue of image decodes or retained output documents.
    private var previewTask: Task<Void, Never>?
    private var previewWorker: Task<PagePreview, Error>?
    private var pendingPreview: PreviewRequest?
    private var previewGeneration = UUID()

    public init() {}
    public var activePreset: WorkflowPreset? {
        WorkflowPreset.allCases.first { $0.maxBytes == byteLimit && $0.settings == settings && $0.profile == profile }
    }
    public func applyPreset(_ preset: WorkflowPreset) {
        guard !busy else { return }
        megabytes = String(Double(preset.maxBytes) / 1_000_000)
        paper = preset.settings.paper; margin = String(preset.settings.margin)
        profile = preset.profile
    }
    public func batch(_ action: PageBatchAction) {
        if selection.apply(action, isBusy: busy) { invalidate() }
    }
    public var inputs: [PageEntry] { selection.entries }
    public var byteLimit: Int? {
        guard let number = Double(megabytes), number.isFinite, number >= 0.01, number <= 100 else { return nil }
        return Int(number * 1_000_000)
    }
    public var settings: PageSettings? {
        guard let points = Double(margin), points.isFinite, (0...72).contains(points) else { return nil }
        let value = PageSettings(paper: paper, margin: points)
        guard (try? value.validate()) != nil else { return nil }
        return value
    }
    public func invalidate() {
        result = nil; reviewed = false; message = ""
        requestPreview()
    }
    public func add(_ urls: [URL]) {
        guard !busy else { return }
        guard inputs.count + urls.count <= 20 else { message = "Choose at most 20 pages. Remove some images first."; return }
        let selectedID = selection.selectedID
        selection = PageSelection(entries: inputs + urls.map { PageEntry(url: $0) })
        if let selectedID { selection.select(selectedID) }
        invalidate()
    }
    public func choose() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.jpeg, .png, .heic]
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.message = "Select still images. Existing PDFs are not supported."
        if panel.runModal() == .OK { add(panel.urls) }
    }
    public func select(_ id: UUID) {
        guard selection.selectedID != id else { return }
        selection.select(id); requestPreview()
    }
    public func step(_ offset: Int) {
        let previous = selection.selectedID
        selection.step(offset)
        if previous != selection.selectedID { requestPreview() }
    }
    public func rotate(_ id: UUID) {
        guard !busy else { return }
        selection.select(id); selection.rotateSelected(); invalidate()
    }
    public func remove(_ id: UUID) {
        guard !busy else { return }
        selection.remove(id); invalidate()
    }
    public func move(_ id: UUID, to target: UUID) {
        guard !busy else { return }
        selection.move(id, to: target); invalidate()
    }
    public func requestPreview() {
        stopPreview()
        guard !busy, let entry = selection.selected, let index = selection.selectedIndex,
              let settings else { return }
        previewLoading = true
        pendingPreview = PreviewRequest(generation: previewGeneration, page: entry.page,
                                        settings: settings, output: result?.data, index: index)
        startNextPreview()
    }
    private func startNextPreview() {
        guard previewTask == nil, let request = pendingPreview else { return }
        pendingPreview = nil
        let job = Task.detached(priority: .userInitiated) {
            try Task.checkCancellation()
            let source = try SourcePreview.render(page: request.page, settings: request.settings)
            try Task.checkCancellation()
            let output = try request.output.map { try ReviewDocument.page(data: $0, at: request.index) }
            try Task.checkCancellation()
            return PagePreview(source: source, output: output)
        }
        previewWorker = job
        previewTask = Task { [weak self] in
            let outcome = await job.result
            guard let self else { return }
            if self.previewGeneration == request.generation {
                switch outcome {
                case .success(let pair): self.preview = pair
                case .failure(let error):
                    if !(error is CancellationError) { self.previewError = error.localizedDescription }
                }
                self.previewLoading = false
            }
            self.previewWorker = nil; self.previewTask = nil
            self.startNextPreview()
        }
    }
    private func stopPreview() {
        previewGeneration = UUID(); pendingPreview = nil
        previewWorker?.cancel()
        preview = nil; previewLoading = false; previewError = ""
    }
    public func prepare() {
        guard !busy, let limit = byteLimit, let settings, !inputs.isEmpty else { return }
        result = nil; reviewed = false; message = ""
        stopPreview(); busy = true
        progress = nil; cancelling = false
        let pages = inputs.map(\.page); let id = UUID(); generation = id
        let owner = self
        let profile = self.profile
        let job = Task.detached(priority: .userInitiated) {
            try Preparation.run(pages: pages, settings: settings, profile: profile, maxBytes: limit) { event in
                Task { @MainActor in
                    guard owner.generation == id, owner.busy else { return }
                    owner.progress = event
                }
            }
        }
        worker = job
        task = Task { [weak self] in
            do {
                let prepared = try await job.value
                guard let self, self.generation == id else { return }
                self.busy = false; self.worker = nil; self.task = nil
                if self.cancelling {
                    self.cancelling = false; self.message = "Preparation cancelled."
                } else {
                    self.result = prepared
                    self.message = "Fits the limit. Inspect every page before saving."
                }
                self.requestPreview()
            } catch {
                guard let self, self.generation == id else { return }
                self.message = error is CancellationError ? "Preparation cancelled." : error.localizedDescription
                self.busy = false; self.cancelling = false; self.worker = nil; self.task = nil
                self.requestPreview()
            }
        }
    }
    public func cancel() {
        guard busy else { return }
        cancelling = true; worker?.cancel(); message = "Stopping after the current image…"
    }
    public func shutdown() {
        generation = UUID(); worker?.cancel(); task?.cancel()
        stopPreview()
    }
    public func save() {
        guard let result, reviewed else { return }
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.pdf]
        panel.nameFieldStringValue = "Prepared.pdf"
        panel.message = "Choose a new filename. Prepare never overwrites an existing file."
        if panel.runModal() == .OK, let url = panel.url {
            do { try Preparation.save(result, to: url); message = "Saved a separate copy: " + url.lastPathComponent }
            catch { message = "Not saved: " + error.localizedDescription + " Choose a new filename." }
        }
    }
}
