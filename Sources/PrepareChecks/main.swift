import Foundation
import CoreGraphics
import ImageIO
import PDFKit
import UniformTypeIdentifiers
import PrepareCore
import PrepareWorkspace

func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() { throw NSError(domain: "PrepareChecks", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
}
if CommandLine.arguments.contains("--ui-contract") { try checkUIContract() }
try require(PageOrder.moving(["a", "b", "c"], from: 0, to: 2) == ["b", "c", "a"], "Dragging a page to the end preserves every item")
try require(PageOrder.moving(["a", "b", "c"], from: 2, to: 0) == ["c", "a", "b"], "Dragging to the beginning preserves order")
try require(PageOrder.moving(["a", "a"], from: -1, to: 0) == ["a", "a"], "Invalid drag is ignored")
let folder = FileManager.default.temporaryDirectory.appendingPathComponent("PrepareChecks-" + UUID().uuidString)
try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: folder) }
let input = folder.appendingPathComponent("original.png")
let context = CGContext(data: nil, width: 1200, height: 1600, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
context.setFillColor(CGColor(gray: 1, alpha: 1)); context.fill(CGRect(x: 0,y: 0,width: 1200,height: 1600))
context.setFillColor(CGColor(gray: 0, alpha: 1))
for y in stride(from: 100, to: 1500, by: 50) { context.fill(CGRect(x: 80,y: y,width: 1040,height: 12)) }
let destination = CGImageDestinationCreateWithURL(input as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(destination, context.makeImage()!, nil)
try require(CGImageDestinationFinalize(destination), "fixture PNG must write")
let before = try Data(contentsOf: input)
final class ProgressLog: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [PreparationProgress] = []
    func append(_ event: PreparationProgress) { lock.lock(); defer { lock.unlock() }; storage.append(event) }
    var events: [PreparationProgress] { lock.lock(); defer { lock.unlock() }; return storage }
}
let log = ProgressLog()
let result = try Preparation.run(inputs: [input, input], maxBytes: 500_000) { log.append($0) }
try require(log.events.count >= 2, "Progress must report actual page work")
try require(log.events.last?.page == 2, "Progress must reach final page")
try require(result.originalBytes == before.count * 2, "Metrics count bytes for every selected page")
try require(result.data.count <= 500_000, "PDF must fit the byte limit")
let pdf = PDFDocument(data: result.data)
try require(pdf?.pageCount == 2, "PDF must reopen with two pages")
try require(pdf?.page(at: 0)?.thumbnail(of: CGSize(width: 100,height: 100), for: .mediaBox).size.width ?? 0 > 0, "PDF must render")
let after = try Data(contentsOf: input)
try require(after == before, "source must remain unchanged")
print("PASS: two-page PDF fits, reopens, renders, original unchanged (\(result.data.count) bytes)")
func rejects(_ name: String, _ operation: () throws -> Void) throws {
    do { try operation() } catch { print("PASS: rejects \(name)"); return }
    throw NSError(domain: "PrepareChecks", code: 2, userInfo: [NSLocalizedDescriptionKey: "Expected rejection: " + name])
}
try rejects("empty input") { _ = try Preparation.run(inputs: [], maxBytes: 500_000) }
try rejects("impossible size") { _ = try Preparation.run(inputs: [input], maxBytes: 1) }
try rejects("negative size") { _ = try Preparation.run(inputs: [input], maxBytes: -1) }
let fake = folder.appendingPathComponent("fake.png")
try Data("not an image".utf8).write(to: fake)
try rejects("fake extension") { _ = try Preparation.run(inputs: [fake], maxBytes: 500_000) }
do {
    _ = try Preparation.run(inputs: [fake], maxBytes: 500_000)
} catch {
    try require(error.localizedDescription.contains("fake.png"), "Unreadable input error must name the offending file")
}

let pdfInput = folder.appendingPathComponent("input.pdf")
try result.data.write(to: pdfInput)
try rejects("existing PDF input") { _ = try Preparation.run(inputs: [pdfInput], maxBytes: 500_000) }
try rejects("too many pages") { _ = try Preparation.run(inputs: Array(repeating: input, count: 21), maxBytes: 500_000) }
let cancellationInput = input
let cancelledJob = Task.detached {
    try Preparation.run(inputs: [cancellationInput], maxBytes: 1_000_000) { _ in
        withUnsafeCurrentTask { $0?.cancel() }
    }
}
do {
    _ = try await cancelledJob.value
    throw NSError(domain: "PrepareChecks", code: 3, userInfo: [NSLocalizedDescriptionKey: "Cancellation during final page must not return success"])
} catch is CancellationError { print("PASS: final-page cancellation propagated") }
let saved = folder.appendingPathComponent("prepared.pdf")
try Preparation.save(result, to: saved)
let savedData = try Data(contentsOf: saved)
try require(savedData == result.data, "saved output must exactly match preview")
try rejects("overwrite source") { try Preparation.save(result, to: input) }
try rejects("overwrite output") { try Preparation.save(result, to: saved) }
print("PASS: export bytes match preview and existing files are protected")


// Render exported PDF pixels, not just PDF geometry. Coordinates are bottom-left.
func renderedPage(_ data: Data, index: Int = 1) throws -> CGContext {
    let document = CGPDFDocument(CGDataProvider(data: data as CFData)!)!
    let page = document.page(at: index)!
    let box = page.getBoxRect(.mediaBox)
    let bitmap = CGContext(data: nil, width: Int(ceil(box.width)), height: Int(ceil(box.height)),
                           bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                           bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    bitmap.setFillColor(CGColor(gray: 1, alpha: 1)); bitmap.fill(box)
    bitmap.drawPDFPage(page)
    return bitmap
}
func color(_ bitmap: CGContext, x: Int, y: Int) -> [Int] {
    let bytes = bitmap.data!.assumingMemoryBound(to: UInt8.self)
    let offset = (bitmap.height - 1 - y) * bitmap.bytesPerRow + x * 4
    return (0..<3).map { Int(bytes[offset + $0]) }
}
let asymmetric = folder.appendingPathComponent("quadrants.png")
let quadrants = CGContext(data: nil, width: 400, height: 200, bitsPerComponent: 8, bytesPerRow: 0,
                         space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
for (rect, rgb) in [(CGRect(x: 0, y: 100, width: 200, height: 100), [1.0, 0, 0]),
                    (CGRect(x: 200, y: 100, width: 200, height: 100), [0.0, 1, 0]),
                    (CGRect(x: 0, y: 0, width: 200, height: 100), [0.0, 0, 1]),
                    (CGRect(x: 200, y: 0, width: 200, height: 100), [1.0, 1, 0])] {
    quadrants.setFillColor(CGColor(red: rgb[0], green: rgb[1], blue: rgb[2], alpha: 1)); quadrants.fill(rect)
}
let quadrantWriter = CGImageDestinationCreateWithURL(asymmetric as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(quadrantWriter, quadrants.makeImage()!, nil)
try require(CGImageDestinationFinalize(quadrantWriter), "Asymmetric fixture writes")
let rotated = try Preparation.run(pages: [PreparationPage(url: asymmetric, rotation: .clockwise90)], maxBytes: 1_000_000)
let rotatedPDF = PDFDocument(data: rotated.data)!
try require(rotatedPDF.page(at: 0)!.bounds(for: .mediaBox).size == CGSize(width: 360, height: 720), "Quarter turn swaps original page dimensions")
let rotatedPixels = try renderedPage(rotated.data)
try require(color(rotatedPixels, x: 270, y: 540)[0] > 220 && color(rotatedPixels, x: 270, y: 540)[1] < 60,
            "Clockwise turn moves original top-left red to top-right in rendered PDF")
try require(color(rotatedPixels, x: 90, y: 540)[2] > 220, "Clockwise turn moves blue to top-left")
print("PASS: clockwise rotation verified in exported PDF pixels")
let letter = try Preparation.run(pages: [PreparationPage(url: asymmetric)], settings: PageSettings(paper: .usLetter, margin: 36), maxBytes: 1_000_000)
let letterBox = PDFDocument(data: letter.data)!.page(at: 0)!.bounds(for: .mediaBox)
try require(letterBox.size == CGSize(width: 612, height: 792), "US Letter media box is exactly 612 × 792 points")
let letterPixels = try renderedPage(letter.data)
try require(color(letterPixels, x: 18, y: 396).allSatisfy { $0 > 245 }, "Letter left margin renders white")
try require(color(letterPixels, x: 50, y: 450)[0] > 220 && color(letterPixels, x: 50, y: 450)[1] < 60, "Letter content fits without cropping or stretching")
print("PASS: US Letter paper and point margins rendered")
for margin in [-1.0, .nan, .infinity, 361] {
    try rejects("invalid margin \(margin)") {
        _ = try Preparation.run(pages: [PreparationPage(url: asymmetric)], settings: PageSettings(margin: margin), maxBytes: 1_000_000)
    }
}
try rejects("margin consumes narrow original page") {
    _ = try Preparation.run(pages: [PreparationPage(url: asymmetric)], settings: PageSettings(margin: 180), maxBytes: 1_000_000)
}
try rejects("zero image dimension") { _ = try PageSettings().layout(width: 0, height: 100, rotation: .none) }
try rejects("non-file input URL") {
    _ = try Preparation.run(pages: [PreparationPage(url: URL(string: "https://example.invalid/image.png")!)], maxBytes: 1_000_000)
}

let a4 = try Preparation.run(pages: [PreparationPage(url: asymmetric, rotation: .clockwise270)], settings: PageSettings(paper: .a4, margin: 24), maxBytes: 1_000_000)
let a4Box = PDFDocument(data: a4.data)!.page(at: 0)!.bounds(for: .mediaBox)
try require(abs(a4Box.width - 210 * 72 / 25.4) < 0.01 && abs(a4Box.height - 297 * 72 / 25.4) < 0.01, "A4 physical size in points")
let a4Pixels = try renderedPage(a4.data)
try require(color(a4Pixels, x: 297, y: 12).allSatisfy { $0 > 245 }, "A4 bottom margin is white")
try require(color(a4Pixels, x: 160, y: 240)[0] > 220 && color(a4Pixels, x: 160, y: 240)[1] < 60, "270-degree rotation keeps red bottom-left on A4")
let legacy = try Preparation.run(inputs: [asymmetric], maxBytes: 1_000_000)
let defaults = try Preparation.run(pages: [PreparationPage(url: asymmetric)], settings: PageSettings(), maxBytes: 1_000_000)
try require(PDFDocument(data: legacy.data)!.page(at: 0)!.bounds(for: .mediaBox).size == CGSize(width: 720, height: 360), "Legacy original aspect and 720-point edge remain default")
let legacyPixels = try renderedPage(legacy.data), defaultPixels = try renderedPage(defaults.data)
for (x, y) in [(90, 90), (90, 270), (630, 90), (630, 270)] {
    try require(color(legacyPixels, x: x, y: y) == color(defaultPixels, x: x, y: y), "Compatibility API and new defaults render identically")
}
// v0.4 profiles: explicit Balanced preserves legacy output; Small File starts lower.
let balanced = try Preparation.run(pages: [PreparationPage(url: asymmetric)], profile: .balanced, maxBytes: 1_000_000)
let small = try Preparation.run(pages: [PreparationPage(url: asymmetric)], profile: .smallFile, maxBytes: 1_000_000)
try require(balanced.longestEdge == 2400 && balanced.quality == 0.85, "Balanced retains the legacy first attempt")
try require(small.longestEdge == 1600 && small.quality == 0.65, "Small File starts at 1600 px and 0.65 quality")
try require(small.profile == .smallFile && balanced.profile == .balanced, "Result records the selected profile")
let balancedPixels = try renderedPage(balanced.data)
try require(color(balancedPixels, x: 90, y: 270) == color(legacyPixels, x: 90, y: 270), "Explicit Balanced preserves legacy rendered color")
let smallFloorLog = ProgressLog()
try rejects("Small File impossible budget") {
    _ = try Preparation.run(pages: [PreparationPage(url: asymmetric)], profile: .smallFile, maxBytes: 1) { smallFloorLog.append($0) }
}
try require(smallFloorLog.events.map(\.pass) == [1, 2, 3], "Small File stops after three bounded attempts at the shared floor")
print("PASS: Balanced compatibility, Small File first attempt and bounded floor")
try require(CompressionProfile(rawValue: "grayscale") != nil, "Grayscale profile must be available")
let grayProfile = CompressionProfile(rawValue: "grayscale")!
let grayscale = try Preparation.run(pages: [PreparationPage(url: asymmetric)], profile: grayProfile, maxBytes: 1_000_000)
let grayPixels = try renderedPage(grayscale.data)
var grayLevels: [Int] = []
for (x, y) in [(90, 90), (90, 270), (630, 90), (630, 270)] {
    let sample = color(grayPixels, x: x, y: y)
    try require(sample.max()! - sample.min()! <= 2, "Grayscale output renders neutral RGB channels")
    grayLevels.append(sample[0])
}
try require(Set(grayLevels).count == 4, "Grayscale preserves distinct tonal values, not blank or thresholded output")
let colorSource = try SourcePreview.render(page: PreparationPage(url: asymmetric), settings: PageSettings())
let sourceColor = color(try renderedPage(colorSource), x: 90, y: 270)
try require(sourceColor[0] > 220 && sourceColor[1] < 60, "Source preview remains original color when output is grayscale")
try require(grayscale.data.count <= 1_000_000 && grayscale.profile == grayProfile, "Grayscale respects exact budget and records profile")
try require(grayscale.data.range(of: Data("/DeviceGray".utf8)) != nil, "PDF embeds a single-component grayscale image, not display-only desaturation")
for profile in CompressionProfile.allCases {
    let profileJob = Task.detached {
        try Preparation.run(inputs: [asymmetric], profile: profile, maxBytes: 1_000_000) { _ in
            withUnsafeCurrentTask { $0?.cancel() }
        }
    }
    do {
        _ = try await profileJob.value
        try require(false, "Every profile honors final-page cancellation")
    } catch is CancellationError { }
}
print("PASS: embedded DeviceGray colorspace and final-page cancellation for every profile")
let grayFloorLog = ProgressLog()
try rejects("Grayscale impossible budget") {
    _ = try Preparation.run(inputs: [asymmetric], profile: grayProfile, maxBytes: 1) { grayFloorLog.append($0) }
}
try require(grayFloorLog.events.count == 5, "Grayscale is bounded to five passes")
print("PASS: true grayscale output pixels, distinct tones, color source and bounded attempts")
let portal = WorkflowPreset.portal500KB
try require(portal.maxBytes == 500_000 && portal.profile == .smallFile && portal.settings == PageSettings(), "Portal preset uses exact decimal 500 KB with original layout and Small File")
let application = WorkflowPreset.application2MB
try require(application.maxBytes == 2_000_000 && application.profile == .balanced && application.settings == PageSettings(paper: .a4, margin: 24), "Application preset uses 2 MB, Balanced, A4 and 24 pt margins")
let photo = WorkflowPreset.photoOriginal
try require(photo.maxBytes == 10_000_000 && photo.profile == .balanced && photo.settings == PageSettings(), "Photo preset uses 10 MB and original aspect, not original resolution")
for preset in WorkflowPreset.allCases {
    let prepared = try Preparation.run(pages: [PreparationPage(url: asymmetric)], settings: preset.settings, profile: preset.profile, maxBytes: preset.maxBytes)
    try require(prepared.data.count <= preset.maxBytes, "Every preset produces output within its exact budget")
    let box = PDFDocument(data: prepared.data)!.page(at: 0)!.bounds(for: .mediaBox)
    let expected = try preset.settings.layout(width: 400, height: 200, rotation: .none)
    try require(abs(box.width - expected.paper.width) < 0.01 && abs(box.height - expected.paper.height) < 0.01, "Preset output has requested physical geometry")
}
print("PASS: Portal, Application and Photo preset budgets, profiles and rendered page geometry")
let turns: [PageRotation] = [.none, .clockwise90, .clockwise180, .clockwise270]
let redLocations = [(180, 270), (270, 540), (540, 90), (90, 180)]
let allTurns = try Preparation.run(pages: turns.map { PreparationPage(url: asymmetric, rotation: $0) }, maxBytes: 2_000_000)
for (index, location) in redLocations.enumerated() {
    let pixels = try renderedPage(allTurns.data, index: index + 1)
    let sample = color(pixels, x: location.0, y: location.1)
    try require(sample[0] > 220 && sample[1] < 60, "Every quarter turn renders in selected page order")
}
try require(PageRotation.none.next.next.next.next == .none, "Four clockwise turns restore original orientation")
print("PASS: A4, all rotations, page order, legacy default geometry and pixels")
let entryA = PageEntry(url: input), entryB = PageEntry(url: input), entryC = PageEntry(url: asymmetric)
var selection = PageSelection(entries: [entryA, entryB, entryC])
selection.select(entryB.id)
selection.move(entryB.id, to: entryC.id)
try require(selection.selectedIndex == 2 && selection.selected?.id == entryB.id, "Selection follows identity through reordering duplicate filenames")
selection.rotateSelected()
try require(selection.selected?.rotation == .clockwise90 && selection.entries[0].rotation == .none, "Rotation affects only selected identity")
selection.remove(entryB.id)
try require(selection.selected?.id == entryC.id, "Removing selected last page selects nearest remaining page")
selection.step(-1)
try require(selection.selected?.id == entryA.id, "Previous page navigation follows displayed order")
selection.step(-1)
try require(selection.selectedIndex == 0, "Navigation clamps to first page")
selection.remove(entryA.id); selection.remove(entryC.id)
try require(selection.selected == nil && selection.selectedIndex == nil, "Empty collection clears selection")
print("PASS: page identity, rotation, reordering, removal and bounded navigation")
let batchEntries = ["page10.png", "page2.png", "page1.png", "page2.png"].map { PageEntry(url: folder.appendingPathComponent($0)) }
var batch = PageSelection(entries: batchEntries)
batch.select(batchEntries[3].id)
try require(batch.apply(.sortByFilename), "Filename sort changes unsorted pages")
try require(batch.entries.map(\.id) == [batchEntries[2].id, batchEntries[1].id, batchEntries[3].id, batchEntries[0].id], "Natural filename sort places page2 before page10 and keeps ties stable")
try require(batch.selectedID == batchEntries[3].id && batch.selectedIndex == 2, "Sort preserves selected identity")
try require(!batch.apply(.sortByFilename), "Already sorted is a no-op")
let sortedEntries = batch.entries
try require(!batch.apply(.clear, isBusy: true) && batch.entries == sortedEntries, "Busy guard prevents destructive batch edits")
try require(batch.apply(.reverse) && batch.selectedIndex == 1, "Reverse preserves selected identity")
let reversedIDs = batch.entries.map(\.id)
try require(batch.apply(.rotateAll) && batch.entries.allSatisfy { $0.rotation == .clockwise90 }, "Rotate all turns every page clockwise")
try require(batch.entries.map(\.id) == reversedIDs && batch.selectedID == batchEntries[3].id, "Rotate all preserves order and selection")
for _ in 0..<3 { _ = batch.apply(.rotateAll) }
try require(batch.entries.allSatisfy { $0.rotation == .none }, "Four batch rotations restore orientation")
try require(batch.apply(.clear) && batch.entries.isEmpty && batch.selectedID == nil, "Clear releases entries and selection")
for action in PageBatchAction.allCases {
    try require(!batch.apply(action), "Every action is a no-op on empty input")
}
var single = PageSelection(entries: [batchEntries[0]])
try require(!single.apply(.reverse) && !single.apply(.sortByFilename), "Single-page reorder is a no-op")
try require(single.apply(.rotateAll), "Single-page rotate all still works")
print("PASS: natural stable sort, reverse, batch rotation, clear, selection identity and busy/empty guards")
let workspace = Workspace()
workspace.add([input, asymmetric])
workspace.select(workspace.inputs[1].id)
let selectedWorkspaceID = workspace.selection.selectedID
workspace.applyPreset(.application2MB)
try require(workspace.settings == application.settings && workspace.byteLimit == application.maxBytes && workspace.profile == application.profile, "Workspace applies every preset field")
try require(workspace.activePreset == .application2MB && workspace.selection.selectedID == selectedWorkspaceID, "Preset indication matches settings without disturbing selected page")
workspace.profile = .grayscale
try require(workspace.activePreset == nil, "Custom profile clears matching preset indicator")
workspace.prepare()
workspace.applyPreset(.portal500KB)
workspace.batch(.clear)
try require(workspace.inputs.count == 2 && workspace.profile == .grayscale, "Busy workspace guards preset and batch actions")
while workspace.busy { try await Task.sleep(for: .milliseconds(10)) }
try require(workspace.result?.profile == .grayscale, "Workspace worker captures and exports chosen profile")
while workspace.previewLoading { try await Task.sleep(for: .milliseconds(10)) }
try require(workspace.preview?.output != nil, "Workspace loads exact selected output for comparison")
workspace.reviewed = true
workspace.profile = .balanced
try require(workspace.result == nil && !workspace.reviewed, "Changing profile invalidates prepared result and review acknowledgment")
workspace.applyPreset(.portal500KB)
try require(workspace.byteLimit == 500_000 && workspace.settings == PageSettings() && workspace.profile == .smallFile, "Preset resets layout, size and compression together")
workspace.prepare()
while workspace.busy { try await Task.sleep(for: .milliseconds(10)) }
try require(workspace.result?.profile == .smallFile, "Integrated Small File preset prepares successfully")
workspace.batch(.reverse)
try require(workspace.result == nil && workspace.selection.selectedID == selectedWorkspaceID, "Batch edit invalidates result and preserves selected identity")
workspace.batch(.clear)
try require(workspace.inputs.isEmpty && workspace.preview == nil && workspace.selection.selectedID == nil, "Clear releases source/output review and selection")
workspace.shutdown()
print("PASS: workspace preset/profile integration, busy guards, exact comparison and stale-result invalidation")
let preview = try SourcePreview.render(page: PreparationPage(url: asymmetric, rotation: .clockwise90), settings: PageSettings(paper: .usLetter, margin: 36))
try require(!preview.isEmpty, "Source comparison produces a downsampled preview document")
let previewPixels = try renderedPage(preview)
try require(color(previewPixels, x: 400, y: 600)[0] > 220 && color(previewPixels, x: 400, y: 600)[1] < 60, "Source comparison uses same clockwise rotation and Letter layout")
try require(color(previewPixels, x: 306, y: 18).allSatisfy { $0 > 245 }, "Source comparison uses same margin")
try rejects("preview invalid input") { _ = try SourcePreview.render(page: PreparationPage(url: fake), settings: PageSettings()) }
let selectedPDF = try ReviewDocument.page(data: allTurns.data, at: 2)
try require(PDFDocument(data: selectedPDF)?.pageCount == 1, "Review contains only exact selected page, cannot drift independently")
let selectedPixels = try renderedPage(selectedPDF)
try require(color(selectedPixels, x: 540, y: 90)[0] > 220 && color(selectedPixels, x: 540, y: 90)[1] < 60, "Review selects exact third page of output")
try rejects("review out of bounds") { _ = try ReviewDocument.page(data: allTurns.data, at: 4) }
try rejects("review negative page") { _ = try ReviewDocument.page(data: allTurns.data, at: -1) }
print("PASS: source comparison layout and exact output page selection")

let tagged = folder.appendingPathComponent("rotated.jpg")
let jpg = CGImageDestinationCreateWithURL(tagged as CFURL, UTType.jpeg.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(jpg, context.makeImage()!, [
    kCGImagePropertyOrientation: 6,
    kCGImagePropertyExifDictionary: [kCGImagePropertyExifUserComment: "PREPARE_PRIVATE_SENTINEL"],
    kCGImagePropertyGPSDictionary: [kCGImagePropertyGPSLatitude: 9.0, kCGImagePropertyGPSLongitude: 7.0]
] as CFDictionary)
try require(CGImageDestinationFinalize(jpg), "JPEG fixture writes")
let mixed = try Preparation.run(inputs: [input, tagged], maxBytes: 1_000_000)
let mixedPDF = PDFDocument(data: mixed.data)!
let first = mixedPDF.page(at: 0)!.bounds(for: .mediaBox)
let second = mixedPDF.page(at: 1)!.bounds(for: .mediaBox)
try require(first.height > first.width && second.width > second.height, "EXIF orientation must rotate the JPEG, preserving mixed input order")
try require(mixed.data.range(of: Data("PREPARE_PRIVATE_SENTINEL".utf8)) == nil, "Source metadata comment is not copied")
print("PASS: mixed PNG/JPEG order, EXIF orientation and metadata sentinel stripping")
let heic = folder.appendingPathComponent("photo.heic")
if let encoder = CGImageDestinationCreateWithURL(heic as CFURL, UTType.heic.identifier as CFString, 1, nil) {
    CGImageDestinationAddImage(encoder, context.makeImage()!, nil)
    try require(CGImageDestinationFinalize(encoder), "HEIC fixture writes")
    let converted = try Preparation.run(inputs: [heic, tagged, input], maxBytes: 2_000_000)
    try require(PDFDocument(data: converted.data)?.pageCount == 3, "Mixed HEIC/JPEG/PNG must reopen")
    print("PASS: HEIC + JPEG + PNG mixed conversion")
} else { print("SKIP: HEIC encoder unavailable on this machine") }
if CommandLine.arguments.contains("--stress") {
    for iteration in 1...12 {
        let profile = CompressionProfile.allCases[(iteration - 1) % CompressionProfile.allCases.count]
        try autoreleasepool {
            let heavy = try Preparation.run(inputs: Array(repeating: tagged, count: 20), profile: profile, maxBytes: 10_000_000)
            try require(PDFDocument(data: heavy.data)?.pageCount == 20, "Stress PDF page count")
            try require(heavy.profile == profile && heavy.data.count <= 10_000_000, "Stress profile and byte limit")
        }
        print("STRESS: batch \(iteration)/12 · \(profile.title) · 20 pages complete")
    }
}
if let flag = CommandLine.arguments.firstIndex(of: "--fixtures"), flag + 1 < CommandLine.arguments.count {
    let dest = URL(fileURLWithPath: CommandLine.arguments[flag + 1])
    try FileManager.default.createDirectory(at: dest, withIntermediateDirectories: true)
    for file in [input, tagged] {
        let target = dest.appendingPathComponent(file.lastPathComponent)
        if !FileManager.default.fileExists(atPath: target.path) { try FileManager.default.copyItem(at: file, to: target) }
    }
    try mixed.data.write(to: dest.appendingPathComponent("Example.pdf"), options: .atomic)
}
