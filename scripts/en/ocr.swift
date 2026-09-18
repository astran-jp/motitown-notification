import Foundation
import Vision
import ImageIO

// usage: ocr <list-file>  -> JSON lines {path, w, h, items:[{text, x, y, w, h, conf}]}
let listPath = CommandLine.arguments[1]
let paths = try! String(contentsOfFile: listPath, encoding: .utf8).split(separator: "\n").map(String.init)
for path in paths {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        print("{\"path\":\"\(path)\",\"error\":\"load\"}"); continue
    }
    let W = Double(img.width), H = Double(img.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["ja-JP", "en-US"]
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    try? handler.perform([req])
    var items: [[String: Any]] = []
    for obs in (req.results ?? []) {
        guard let c = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        items.append(["text": c.string, "x": Int(b.minX * W), "y": Int((1 - b.maxY) * H), "w": Int(b.width * W), "h": Int(b.height * H), "conf": Double(c.confidence)])
    }
    let obj: [String: Any] = ["path": path, "w": Int(W), "h": Int(H), "items": items]
    let data = try! JSONSerialization.data(withJSONObject: obj, options: [])
    print(String(data: data, encoding: .utf8)!)
}
