//
//  PreviewProvider.h
//  GraphSketcherPreview
//
//  Created by Kyusik Chung on 6/25/26.
//

#import <Cocoa/Cocoa.h>
#import <Quartz/Quartz.h>

// Data-based preview provider (returns the document's embedded preview.pdf).
// QLPreviewProvider subclasses must declare conformance to QLPreviewingController (its
// -providePreviewForFileRequest:completionHandler: is how data-based previews are requested);
// without the declared conformance the Quick Look host ignores the extension and falls back to
// the generic file-info card.
@interface PreviewProvider : QLPreviewProvider <QLPreviewingController>

@end
