import Cocoa

let S: CGFloat = 1024
let img = NSImage(size: NSSize(width: S, height: S))
img.lockFocus()

// ---- 背景: 圆角方块 + 靛紫渐变 ----
let bgRect = NSRect(x: 92, y: 92, width: 840, height: 840)
let bgPath = NSBezierPath(roundedRect: bgRect, xRadius: 210, yRadius: 210)
let grad = NSGradient(colors: [
    NSColor(red: 0.42, green: 0.39, blue: 0.96, alpha: 1), // 靛
    NSColor(red: 0.62, green: 0.28, blue: 0.92, alpha: 1), // 紫
])!
grad.draw(in: bgPath, angle: -45)

// 顶部微光
if let hi = NSGraphicsContext.current {
    hi.saveGraphicsState()
    bgPath.addClip()
    NSColor.white.withAlphaComponent(0.06).setFill()
    NSBezierPath(ovalIn: NSRect(x: 240, y: 760, width: 544, height: 220)).fill()
    hi.restoreGraphicsState()
}

// ---- 白色盾牌 ----
let shield = NSBezierPath()
shield.move(to: NSPoint(x: 512, y: 736))                       // 顶部中央凹点
shield.curve(to: NSPoint(x: 316, y: 690), controlPoint1: NSPoint(x: 452, y: 724), controlPoint2: NSPoint(x: 330, y: 706))
shield.line(to: NSPoint(x: 316, y: 500))                       // 左上→左侧
shield.curve(to: NSPoint(x: 512, y: 288), controlPoint1: NSPoint(x: 316, y: 396), controlPoint2: NSPoint(x: 408, y: 330)) // 左侧→底部尖
shield.curve(to: NSPoint(x: 708, y: 500), controlPoint1: NSPoint(x: 616, y: 330), controlPoint2: NSPoint(x: 708, y: 396)) // 底部尖→右侧
shield.line(to: NSPoint(x: 708, y: 690))                       // 右侧→右上
shield.curve(to: NSPoint(x: 512, y: 736), controlPoint1: NSPoint(x: 694, y: 706), controlPoint2: NSPoint(x: 572, y: 724))
shield.close()
NSColor.white.setFill()
shield.fill()

// ---- 双箭头 ⇄ (靛色) ----
let arrowColor = NSColor(red: 0.36, green: 0.33, blue: 0.88, alpha: 1)
arrowColor.setFill()

func arrow(y: CGFloat, pointingRight: Bool) {
    let bar = NSBezierPath(roundedRect: NSRect(x: 396, y: y, width: 176, height: 34), xRadius: 17, yRadius: 17)
    bar.fill()
    let head = NSBezierPath()
    if pointingRight {
        head.move(to: NSPoint(x: 566, y: y - 22))
        head.line(to: NSPoint(x: 648, y: y + 17))
        head.line(to: NSPoint(x: 566, y: y + 56))
    } else {
        head.move(to: NSPoint(x: 458, y: y - 22))
        head.line(to: NSPoint(x: 376, y: y + 17))
        head.line(to: NSPoint(x: 458, y: y + 56))
    }
    head.close()
    head.fill()
}
arrow(y: 550, pointingRight: true)   // 上箭头 →
arrow(y: 428, pointingRight: false)  // 下箭头 ←

img.unlockFocus()

// 保存 PNG
if let tiff = img.tiffRepresentation,
   let rep = NSBitmapImageRep(data: tiff),
   let png = rep.representation(using: .png, properties: [:]) {
    try? png.write(to: URL(fileURLWithPath: "/tmp/switcher-icon-1024.png"))
    print("saved")
}
