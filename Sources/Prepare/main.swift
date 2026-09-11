import SwiftUI
import AppKit
import PDFKit
import UniformTypeIdentifiers
import PrepareCore

import PrepareWorkspace

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

@MainActor
private final class WorkbenchPresentation: ObservableObject {
    @Published var showClearConfirmation = false
}

struct ContentView: View {
    @ObservedObject var model: Workspace
    @StateObject private var presentation = WorkbenchPresentation()
    private let accent = Color(red: 0.16, green: 0.38, blue: 0.32)
    private func size(_ bytes: Int) -> String { String(format: "%.2f MB", Double(bytes) / 1_000_000) }

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
        }.frame(height: 116)
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 8) {
                Label("Prepare", systemImage: "doc.badge.gearshape")
                    .font(.system(size: 27, weight: .semibold, design: .rounded)).foregroundStyle(accent)
                Text("Images to a ready-to-share PDF.").font(.callout).foregroundStyle(.secondary)
                Label("On your Mac · Nothing uploaded", systemImage: "lock.shield")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Divider()
            VStack(alignment: .leading, spacing: 9) {
                Text("Workflow preset").font(.headline)
                ForEach(WorkflowPreset.allCases, id: \.self) { preset in
                    Button { model.applyPreset(preset) } label: {
                        HStack(spacing: 9) {
                            Image(systemName: model.activePreset == preset ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(model.activePreset == preset ? accent : Color.secondary)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(preset.title).font(.callout.weight(.medium))
                                Text(presetDetail(preset)).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer(minLength: 0)
                        }.padding(10).frame(maxWidth: .infinity, alignment: .leading)
                            .background(model.activePreset == preset ? accent.opacity(0.1) : Color.primary.opacity(0.035), in: RoundedRectangle(cornerRadius: 9))
                            .contentShape(Rectangle())
                    }.buttonStyle(.plain).disabled(model.busy)
                        .accessibilityLabel("Apply " + preset.title)
                        .accessibilityValue(model.activePreset == preset ? "Selected" : "Not selected")
                }
                Text(model.activePreset == nil ? "Custom settings · choose a starting point above" : "Starting point only · adjust below")
                    .font(.caption).foregroundStyle(.secondary)
            }
            VStack(alignment: .leading, spacing: 9) {
                Text("Compression profile").font(.headline)
                Picker("Compression profile", selection: $model.profile) {
                    ForEach(CompressionProfile.allCases, id: \.self) { profile in Text(profile.title).tag(profile) }
                }.pickerStyle(.segmented).labelsHidden().disabled(model.busy)
                    .accessibilityLabel("Compression profile")
                Text(profileDetail).font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                HStack {
                    Text("Maximum PDF size").font(.callout)
                    Spacer(minLength: 4)
                    TextField("MB", text: $model.megabytes).textFieldStyle(.roundedBorder).frame(width: 56)
                        .accessibilityLabel("Maximum PDF size in decimal megabytes").disabled(model.busy)
                    Text("MB").foregroundStyle(.secondary)
                }
                if model.byteLimit == nil { Text("Enter 0.01–100 MB.").foregroundStyle(.red).font(.caption) }
            }
            DisclosureGroup("Advanced layout") {
                VStack(alignment: .leading, spacing: 10) {
                    Picker("Paper", selection: $model.paper) {
                        Text("Original aspect").tag(PaperFormat.original)
                        Text("A4").tag(PaperFormat.a4)
                        Text("US Letter").tag(PaperFormat.usLetter)
                    }.accessibilityLabel("Output paper size")
                    Picker("DPI ceiling", selection: $model.dpiCeiling) {
                        ForEach(DPICeiling.allCases, id: \.self) { Text($0.title).tag($0) }
                    }.accessibilityLabel("DPI ceiling")
                        .help("Maximum raster density at the actual placed image size. Never upscales; the byte budget may lower it further.")
                    HStack {
                        Text("Margin")
                        Spacer()
                        TextField("0–72", text: $model.margin).textFieldStyle(.roundedBorder).frame(width: 52)
                            .accessibilityLabel("Page margin in points")
                        Stepper("Margin", value: Binding(get: { model.settings?.margin ?? 0 },
                            set: { model.margin = String(format: "%.0f", $0) }), in: 0...72, step: 1)
                            .labelsHidden().accessibilityLabel("Adjust page margin")
                        Text("pt").foregroundStyle(.secondary)
                    }
                    Text(model.paper == .original ? "Original aspect uses a 720 pt page edge, not original resolution or scan DPI." : "Fits portrait paper without cropping. 72 pt = 1 inch.")
                        .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    Text("DPI limits placed content, never upscales, and may go below 960 px. The byte budget can lower density further.")
                        .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                }.padding(.top, 10).disabled(model.busy)
            }.font(.callout.weight(.medium))
            if model.settings == nil { Text("Enter a margin from 0 to 72 points.").foregroundStyle(.red).font(.caption) }
            VStack(spacing: 10) {
                Button(action: model.prepare) {
                    Label(model.busy ? "Preparing…" : "Prepare PDF", systemImage: "wand.and.stars")
                        .frame(maxWidth: .infinity).padding(.vertical, 5)
                }.buttonStyle(.borderedProminent).tint(accent)
                    .keyboardShortcut("r", modifiers: .command)
                    .disabled(model.inputs.isEmpty || model.byteLimit == nil || model.settings == nil || model.busy)
                if model.busy {
                    if let p = model.progress {
                        ProgressView(value: Double(p.page), total: Double(p.totalPages))
                        Text("Pass \(p.pass) of at most \(model.profile.maximumPasses) · Page \(p.page)/\(p.totalPages)")
                            .font(.caption).foregroundStyle(.secondary).monospacedDigit()
                    } else { ProgressView("Checking images…") }
                    Button(model.cancelling ? "Cancelling…" : "Cancel", action: model.cancel)
                        .disabled(model.cancelling).keyboardShortcut(.cancelAction)
                }
            }
            Text("Originals stay untouched. Transparency becomes white. No PDF input, OCR or accessible-text conversion.")
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
    }
    private func presetDetail(_ preset: WorkflowPreset) -> String {
        switch preset {
        case .portal500KB: "Small File · original aspect · no margins"
        case .application2MB: "Balanced · A4 · 24 pt margins"
        case .photoOriginal: "Balanced · 10 MB · no margins"
        }
    }
    private var profileDetail: String {
        switch model.profile {
        case .balanced: "Color, with more detail to start. Up to 2400 px."
        case .smallFile: "Color, starting at 1600 px and lower JPEG quality. Check small text closely."
        case .grayscale: "Converts output to gray tones. Source stays in original color for comparison."
        }
    }
    private var actionToolbar: some View {
        HStack(spacing: 10) {
            Button(action: model.choose) { Label("Add images…", systemImage: "plus") }
                .keyboardShortcut("o", modifiers: .command).disabled(model.busy)
                .help("JPEG, PNG or HEIC · up to 20 pages. You can also drop files here.")
            Spacer(minLength: 0)
            Menu {
                Button("Duplicate selected", systemImage: "plus.square.on.square") { model.duplicateSelected() }
                    .disabled(model.inputs.count >= 20)
                Button("Move selected to last", systemImage: "arrow.down.to.line") { model.moveSelectedLast() }
                    .disabled(model.selection.selectedIndex == model.inputs.count - 1)
            } label: { Image(systemName: "ellipsis.circle") }
                .menuStyle(.borderlessButton).fixedSize()
                .accessibilityLabel("Selected page actions")
                .help("Duplicate selected page or move it to the end")
                .disabled(model.busy || model.selection.selected == nil)
            Menu {
                Button("Sort by filename") { model.batch(.sortByFilename) }
                    .disabled(model.inputs.count < 2)
                Button("Reverse order") { model.batch(.reverse) }
                    .disabled(model.inputs.count < 2)
            } label: { Label("Order", systemImage: "arrow.up.arrow.down") }
                .menuStyle(.borderlessButton).fixedSize().disabled(model.busy || model.inputs.count < 2)
                .accessibilityLabel("Page order actions")
            Button { model.batch(.rotateAll) } label: { Label("Rotate all", systemImage: "rotate.right") }
                .disabled(model.busy || model.inputs.isEmpty).help("Rotate every page 90° clockwise")
            Button("Clear pages…", role: .destructive) { presentation.showClearConfirmation = true }
                .disabled(model.busy || model.inputs.isEmpty)
        }.controlSize(.regular)
    }
    private var navigation: some View {
        HStack(spacing: 10) {
            Button { model.step(-1) } label: { Image(systemName: "chevron.left") }
                .disabled((model.selection.selectedIndex ?? 0) == 0)
                .keyboardShortcut("[", modifiers: .command).accessibilityLabel("Previous page")
            Text(model.inputs.isEmpty ? "No pages" : "Page \((model.selection.selectedIndex ?? 0) + 1) of \(model.inputs.count)")
                .monospacedDigit().font(.callout.weight(.medium))
            Button { model.step(1) } label: { Image(systemName: "chevron.right") }
                .disabled((model.selection.selectedIndex ?? 0) >= model.inputs.count - 1)
                .keyboardShortcut("]", modifiers: .command).accessibilityLabel("Next page")
            Text(model.selection.selected?.url.lastPathComponent ?? "")
                .font(.caption).foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle)
            Spacer(minLength: 0)
        }
    }
    private func previewPane(_ title: String, data: Data?, placeholder: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.subheadline.weight(.semibold))
            if let data {
                DocumentPreview(data: data, label: "\(title), page \((model.selection.selectedIndex ?? 0) + 1)")
                    .clipShape(RoundedRectangle(cornerRadius: 10))
            } else {
                VStack(spacing: 10) {
                    if model.previewLoading || model.busy { ProgressView() }
                    Image(systemName: title.hasPrefix("Source") ? "photo" : "doc.richtext").font(.title).foregroundStyle(accent.opacity(0.65))
                    Text(placeholder).font(.callout).multilineTextAlignment(.center).foregroundStyle(.secondary)
                }.padding(12).frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(accent.opacity(0.04), in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Color.primary.opacity(0.08)))
            }
        }.frame(minWidth: 0, maxWidth: .infinity, maxHeight: .infinity)
    }
    private var review: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text("Review workbench").font(.title2.weight(.semibold))
                Spacer()
                Text("\(model.inputs.count)/20 pages").font(.caption).monospacedDigit().foregroundStyle(.secondary)
            }
            actionToolbar
            if model.inputs.isEmpty {
                VStack(alignment: .leading, spacing: 5) {
                    Text("Start with your scans or photos").font(.headline)
                    Text("Drop JPEG, PNG or HEIC files here. Choose a preset, then prepare and inspect every page.")
                        .font(.callout).foregroundStyle(.secondary)
                }.padding(14).frame(maxWidth: .infinity, alignment: .leading)
                    .background(accent.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
            } else { pageList }
            Divider()
            navigation
            HStack(alignment: .top, spacing: 14) {
                previewPane("Source · original color", data: model.preview?.source,
                    placeholder: model.inputs.isEmpty ? "Add images to begin" : model.previewLoading ? "Loading selected page…" : "Source preview unavailable")
                previewPane("Exact output · \(model.result?.profile.title ?? model.profile.title)", data: model.preview?.output,
                    placeholder: model.busy ? "Preparing locally…" : model.result == nil ? "Prepare PDF to compare" : "Loading selected page…")
            }.frame(minHeight: 210, maxHeight: .infinity)
            if !model.previewError.isEmpty {
                Text(model.previewError).font(.caption).foregroundStyle(.red).fixedSize(horizontal: false, vertical: true)
            }
            Text("Source is downsampled to ≤ \(SourcePreview.longestEdge) px, not full resolution. Both panes show the same page. Pinch to zoom.")
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            exportFooter
        }
    }
    private var exportFooter: some View {
        VStack(alignment: .leading, spacing: 9) {
            Divider()
            if let result = model.result {
                HStack {
                    Label(size(result.data.count), systemImage: "checkmark.circle.fill")
                        .font(.title3.weight(.semibold)).foregroundStyle(accent)
                    Text("of \(size(model.byteLimit ?? 0)) limit").font(.callout).foregroundStyle(.secondary)
                    Spacer()
                    Text("\(result.data.count.formatted()) bytes").font(.caption).monospacedDigit().foregroundStyle(.secondary)
                }
                Text("\(result.profile.title) · edge ≤ \(result.longestEdge) px · from \(size(result.originalBytes)) of images. Compression can reduce detail; acceptance is not guaranteed.")
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
            if !model.message.isEmpty {
                Text(model.message).font(.callout).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
            }
            HStack(spacing: 12) {
                Toggle("I checked every page for legibility", isOn: $model.reviewed)
                    .toggleStyle(.checkbox).disabled(model.preview?.output == nil || model.result == nil)
                Spacer(minLength: 0)
                Button("Save a copy…", action: model.save)
                    .disabled(model.result == nil || !model.reviewed || model.busy)
                    .keyboardShortcut("s", modifiers: [.command, .shift])
                    .help("Save a separate PDF. Existing files are never replaced.")
            }
        }
    }
    var body: some View {
        HSplitView {
            ScrollView { sidebar.padding(20) }
                .frame(minWidth: 290, idealWidth: 310, maxWidth: 350)
                .background(Color(nsColor: .controlBackgroundColor))
            review.padding(20).frame(minWidth: 620)
        }.frame(minWidth: 950, minHeight: 740)
            .confirmationDialog("Clear all pages?", isPresented: $presentation.showClearConfirmation, titleVisibility: .visible) {
                Button("Clear pages", role: .destructive) { model.batch(.clear) }
                Button("Keep pages", role: .cancel) {}
            } message: { Text("Removes this workspace and its prepared PDF. Original image files are not deleted.") }
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
            .defaultSize(width: 1120, height: 820)
    }
}
