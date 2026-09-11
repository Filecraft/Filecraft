import SwiftUI
import AppKit
import PDFKit
import UniformTypeIdentifiers
import PrepareCore

private struct PreviewRequest: Sendable {
    let generation: UUID
    let page: PreparationPage
    let settings: PageSettings
    let output: Data?
    let index: Int
}

private struct PagePreview: Sendable {
    let source: Data
    let output: Data?
}

@MainActor
final class Workspace: ObservableObject {
    @Published private(set) var selection = PageSelection()
    @Published var progress: PreparationProgress?
    @Published var cancelling = false
    @Published var megabytes = "2" { didSet { if oldValue != megabytes { invalidate() } } }
    @Published var paper: PaperFormat = .original { didSet { if oldValue != paper { invalidate() } } }
    @Published var margin = "0" { didSet { if oldValue != margin { invalidate() } } }
    @Published var result: Prepared?
    @Published var busy = false
    @Published var message = ""
    @Published var reviewed = false
    @Published fileprivate var preview: PagePreview?
    @Published private(set) var previewLoading = false
    @Published private(set) var previewError = ""
    private var task: Task<Void, Never>?
    private var worker: Task<Prepared, Error>?
    private var generation = UUID()
    // One active decode and one replaceable pending request: rapid edits never
    // create an unbounded queue of image decodes or retained output documents.
    private var previewTask: Task<Void, Never>?
    private var previewWorker: Task<PagePreview, Error>?
    private var pendingPreview: PreviewRequest?
    private var previewGeneration = UUID()

    var inputs: [PageEntry] { selection.entries }
    var byteLimit: Int? {
        guard let number = Double(megabytes), number.isFinite, number >= 0.01, number <= 100 else { return nil }
        return Int(number * 1_000_000)
    }
    var settings: PageSettings? {
        guard let points = Double(margin), points.isFinite, (0...72).contains(points) else { return nil }
        let value = PageSettings(paper: paper, margin: points)
        guard (try? value.validate()) != nil else { return nil }
        return value
    }
    func invalidate() {
        result = nil; reviewed = false; message = ""
        requestPreview()
    }
    func add(_ urls: [URL]) {
        guard !busy else { return }
        guard inputs.count + urls.count <= 20 else { message = "Choose at most 20 pages. Remove some images first."; return }
        let selectedID = selection.selectedID
        selection = PageSelection(entries: inputs + urls.map { PageEntry(url: $0) })
        if let selectedID { selection.select(selectedID) }
        invalidate()
    }
    func choose() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.jpeg, .png, .heic]
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.message = "Select still images. Existing PDFs are not supported."
        if panel.runModal() == .OK { add(panel.urls) }
    }
    func select(_ id: UUID) {
        guard selection.selectedID != id else { return }
        selection.select(id); requestPreview()
    }
    func step(_ offset: Int) {
        let previous = selection.selectedID
        selection.step(offset)
        if previous != selection.selectedID { requestPreview() }
    }
    func rotate(_ id: UUID) {
        guard !busy else { return }
        selection.select(id); selection.rotateSelected(); invalidate()
    }
    func remove(_ id: UUID) {
        guard !busy else { return }
        selection.remove(id); invalidate()
    }
    func move(_ id: UUID, to target: UUID) {
        guard !busy else { return }
        selection.move(id, to: target); invalidate()
    }
    func requestPreview() {
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
    func prepare() {
        guard !busy, let limit = byteLimit, let settings, !inputs.isEmpty else { return }
        result = nil; reviewed = false; message = ""
        stopPreview(); busy = true
        progress = nil; cancelling = false
        let pages = inputs.map(\.page); let id = UUID(); generation = id
        let owner = self
        let job = Task.detached(priority: .userInitiated) {
            try Preparation.run(pages: pages, settings: settings, maxBytes: limit) { event in
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
    func cancel() {
        guard busy else { return }
        cancelling = true; worker?.cancel(); message = "Stopping after the current image…"
    }
    func shutdown() {
        generation = UUID(); worker?.cancel(); task?.cancel()
        stopPreview()
    }
    func save() {
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

struct DocumentPreview: NSViewRepresentable {
    let data: Data
    let label: String
    final class Coordinator { var data: Data? }
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true; view.displayMode = .singlePage
        view.displaysPageBreaks = false
        view.backgroundColor = .windowBackgroundColor
        view.setAccessibilityLabel(label)
        // Both Review APIs return one-page documents. PDFKit has no other page
        // to navigate to, but retains native zoom, scrolling and accessibility.
        view.document = PDFDocument(data: data)
        context.coordinator.data = data
        return view
    }
    func updateNSView(_ view: PDFView, context: Context) {
        view.setAccessibilityLabel(label)
        if context.coordinator.data != data {
            view.document = PDFDocument(data: data)
            view.autoScales = true
            context.coordinator.data = data
        }
    }
}

struct ContentView: View {
    @ObservedObject var model: Workspace
    private func size(_ bytes: Int) -> String { String(format: "%.2f MB", Double(bytes) / 1_000_000) }
    private let accent = Color(red: 0.16, green: 0.38, blue: 0.32)

    private var pageList: some View {
        ScrollView {
            LazyVStack(spacing: 6) {
                ForEach(Array(model.inputs.enumerated()), id: \.element.id) { index, entry in
                    HStack(spacing: 6) {
                        Image(systemName: "line.3.horizontal").foregroundStyle(.tertiary)
                        Button { model.select(entry.id) } label: {
                            HStack(spacing: 6) {
                                Text("\(index + 1)").monospacedDigit().frame(width: 18)
                                Text(entry.url.lastPathComponent).lineLimit(1).truncationMode(.middle)
                                Spacer(minLength: 0)
                            }.contentShape(Rectangle())
                        }.buttonStyle(.plain)
                            .accessibilityLabel("Select page \(index + 1), \(entry.url.lastPathComponent)")
                            .accessibilityValue(model.selection.selectedID == entry.id ? "Selected" : "Not selected")
                        Text("\(entry.rotation.rawValue * 90)°").font(.caption).monospacedDigit().frame(width: 28)
                        Button { model.rotate(entry.id) } label: { Image(systemName: "rotate.right") }
                            .disabled(model.busy).help("Rotate this page 90° clockwise")
                            .accessibilityLabel("Rotate page \(index + 1) clockwise")
                        Button {
                            if index > 0 { model.move(entry.id, to: model.inputs[index - 1].id) }
                        } label: { Image(systemName: "arrow.up") }
                            .disabled(index == 0 || model.busy)
                            .accessibilityLabel("Move \(entry.url.lastPathComponent) earlier")
                        Button { model.remove(entry.id) } label: { Image(systemName: "xmark") }
                            .disabled(model.busy).accessibilityLabel("Remove \(entry.url.lastPathComponent)")
                    }.controlSize(.small).padding(8)
                        .background(model.selection.selectedID == entry.id ? accent.opacity(0.14) : Color.primary.opacity(0.04), in: RoundedRectangle(cornerRadius: 8))
                        .draggable(entry.id.uuidString)
                        .dropDestination(for: String.self) { values, _ in
                            guard !model.busy, let value = values.first, let id = UUID(uuidString: value),
                                  model.inputs.contains(where: { $0.id == id }) else { return false }
                            model.move(id, to: entry.id); return true
                        }
                        .help(entry.url.lastPathComponent + " — select to review; drag to reorder")
                }
            }
        }.frame(height: 148)
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "doc.badge.gearshape").font(.title).foregroundStyle(accent)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Prepare").font(.system(size: 28, weight: .semibold, design: .rounded))
                    Text("A smaller file. A simpler handoff.").font(.caption).foregroundStyle(.secondary)
                }
            }
            Label("On your Mac · Nothing uploaded", systemImage: "lock.shield").font(.caption).foregroundStyle(.secondary)
            Divider()
            HStack {
                Text("1  Choose images").font(.headline)
                Spacer()
                Button("Add images…", action: model.choose).disabled(model.busy)
                    .keyboardShortcut("o", modifiers: .command)
                    .help("Add JPEG, PNG or HEIC images. You can also drop files here.")
            }
            if model.inputs.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "photo.on.rectangle.angled").font(.system(size: 28)).foregroundStyle(accent)
                    Text("Start with your scans or photos").font(.headline)
                    Text("JPEG, PNG or HEIC · up to 20 pages\nDrop files here or use Add images.")
                        .font(.caption).multilineTextAlignment(.center).foregroundStyle(.secondary)
                }.frame(maxWidth: .infinity, minHeight: 148)
                    .background(accent.opacity(0.06), in: RoundedRectangle(cornerRadius: 12))
            } else { pageList }
            Text("2  Set page layout & size").font(.headline)
            Picker("Paper", selection: $model.paper) {
                Text("Original").tag(PaperFormat.original)
                Text("A4").tag(PaperFormat.a4)
                Text("US Letter").tag(PaperFormat.usLetter)
            }.disabled(model.busy).accessibilityLabel("Output paper size")
            HStack {
                Text("Margin")
                TextField("0–72", text: $model.margin).textFieldStyle(.roundedBorder).frame(width: 52)
                    .accessibilityLabel("Page margin in points, zero to seventy-two")
                Stepper("Margin", value: Binding(get: {
                    model.settings?.margin ?? 0
                }, set: { model.margin = String(format: "%.0f", $0) }), in: 0...72, step: 1)
                    .labelsHidden().accessibilityLabel("Adjust page margin in points")
                Text("pt · 72 = 1 inch").font(.caption).foregroundStyle(.secondary)
                Spacer(minLength: 0)
            }.disabled(model.busy)
            if model.settings == nil { Text("Enter a margin from 0 to 72 points.").foregroundStyle(.red).font(.caption) }
            Text(model.paper == .original ? "Original keeps image aspect ratio (720 pt longest edge), not scan DPI." : "Images fit on portrait paper without cropping or stretching.")
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            HStack {
                Text("Maximum PDF size")
                Spacer()
                TextField("MB", text: $model.megabytes).textFieldStyle(.roundedBorder).frame(width: 60)
                    .accessibilityLabel("Maximum PDF size in decimal megabytes").disabled(model.busy)
                Text("MB").foregroundStyle(.secondary)
            }
            if model.byteLimit == nil { Text("Enter a size from 0.01 to 100 MB.").foregroundStyle(.red).font(.caption) }
            HStack {
                Button(action: model.prepare) {
                    Label(model.busy ? "Preparing…" : "Prepare PDF", systemImage: "wand.and.stars")
                        .frame(maxWidth: .infinity).padding(.vertical, 3)
                }.buttonStyle(.borderedProminent).tint(accent)
                    .keyboardShortcut("r", modifiers: .command)
                    .disabled(model.inputs.isEmpty || model.byteLimit == nil || model.settings == nil || model.busy)
                if model.busy {
                    Button(model.cancelling ? "Cancelling…" : "Cancel", action: model.cancel)
                        .disabled(model.cancelling).keyboardShortcut(.cancelAction)
                }
            }
            if model.busy {
                if let p = model.progress {
                    ProgressView(value: Double(p.page), total: Double(p.totalPages))
                    Text("Pass \(p.pass) of at most 5 · Page \(p.page) of \(p.totalPages)")
                        .font(.caption).foregroundStyle(.secondary).monospacedDigit()
                } else { ProgressView("Checking images…") }
            }
            if !model.message.isEmpty {
                Text(model.message).font(.callout).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
            }
            Text("Originals are never overwritten. Transparency becomes white. No PDF input, OCR or accessible-text conversion.")
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
    }

    private var navigation: some View {
        HStack {
            Button { model.step(-1) } label: { Image(systemName: "chevron.left") }
                .disabled((model.selection.selectedIndex ?? 0) == 0)
                .keyboardShortcut("[", modifiers: .command).accessibilityLabel("Previous page")
            Text("Page \((model.selection.selectedIndex ?? 0) + 1) of \(model.inputs.count)")
                .monospacedDigit().font(.callout)
            Button { model.step(1) } label: { Image(systemName: "chevron.right") }
                .disabled((model.selection.selectedIndex ?? 0) >= model.inputs.count - 1)
                .keyboardShortcut("]", modifiers: .command).accessibilityLabel("Next page")
            Spacer(minLength: 0)
        }
    }

    private func previewPane(_ title: String, data: Data?, placeholder: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.subheadline.weight(.semibold))
            if let data {
                DocumentPreview(data: data, label: "\(title), page \((model.selection.selectedIndex ?? 0) + 1)")
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                VStack(spacing: 10) {
                    if model.previewLoading || model.busy { ProgressView() }
                    Text(placeholder).font(.callout).multilineTextAlignment(.center).foregroundStyle(.secondary)
                }.padding(12).frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.quaternary.opacity(0.25), in: RoundedRectangle(cornerRadius: 8))
            }
        }.frame(minWidth: 0, maxWidth: .infinity, maxHeight: .infinity)
    }

    private var review: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("3  Compare & review").font(.headline)
            if !model.inputs.isEmpty {
                navigation
                Text(model.selection.selected?.url.lastPathComponent ?? "")
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle)
            }
            if let result = model.result {
                VStack(alignment: .leading, spacing: 4) {
                    Text(result.data.count < result.originalBytes ? "Reduced from \(size(result.originalBytes)) to \(size(result.data.count))" : "Prepared \(size(result.data.count)) from \(size(result.originalBytes)) of images")
                        .font(.headline)
                    Text("\(result.pageCount) pages · \(result.data.count.formatted()) bytes · within your limit")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            HStack(alignment: .top, spacing: 12) {
                previewPane("Source · downsampled", data: model.preview?.source,
                            placeholder: model.inputs.isEmpty ? "Add images to begin" : model.previewLoading ? "Loading selected page…" : "Source preview unavailable")
                previewPane("Exact output page", data: model.preview?.output,
                            placeholder: model.busy ? "Preparing locally…" : model.result == nil ? "Prepare PDF to compare" : "Loading selected page…")
            }.frame(maxHeight: .infinity)
            if !model.previewError.isEmpty {
                Text(model.previewError).font(.caption).foregroundStyle(.red).fixedSize(horizontal: false, vertical: true)
            }
            Text("Source is downsampled to ≤ \(SourcePreview.longestEdge) px, not full resolution. Both panes follow the page selector; pinch to zoom and inspect small text.")
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            if let result = model.result {
                Text("Output edge ≤ \(result.longestEdge) px. Compression can reduce detail. Website acceptance and readability are not guaranteed.")
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                Toggle("I checked every page for legibility", isOn: $model.reviewed)
                    .toggleStyle(.checkbox).disabled(model.preview?.output == nil)
                HStack {
                    Spacer()
                    Button("Save a copy…", action: model.save).disabled(!model.reviewed)
                        .keyboardShortcut("s", modifiers: [.command, .shift])
                        .help("Save the reviewed PDF to a new path. Existing files are never replaced.")
                }
            }
        }
    }

    var body: some View {
        HSplitView {
            ScrollView { controls.padding(18) }
                .frame(minWidth: 350, idealWidth: 380, maxWidth: 430)
            review.padding(18).frame(minWidth: 400)
        }
        .frame(minWidth: 850, minHeight: 620)
        .dropDestination(for: URL.self) { urls, _ in
            guard !model.busy else { return false }; model.add(urls); return true
        }
        .onDisappear { model.shutdown() }
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    let workspace = Workspace()
    func application(_ application: NSApplication, open urls: [URL]) {
        workspace.add(urls.filter(\.isFileURL))
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        // Do not steal focus when launched in the background.
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
@main
struct PrepareApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    var body: some Scene {
        Window("Prepare", id: "workspace") { ContentView(model: delegate.workspace) }
            .defaultSize(width: 1000, height: 700)
    }
}
