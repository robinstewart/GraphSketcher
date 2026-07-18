//
//  PreviewProvider.m
//  GraphSketcherPreview
//
//  Data-based Quick Look preview for GraphSketcher (.ograph) documents: returns the vector chart
//  preview (preview.pdf) embedded in each document. See OGraphPreviewExtraction.h.
//

#import "PreviewProvider.h"
#import <CoreGraphics/CoreGraphics.h>
#import <PDFKit/PDFKit.h>
#import "../OGraphPreviewExtraction.h"

@implementation PreviewProvider

- (void)providePreviewForFileRequest:(QLFilePreviewRequest *)request completionHandler:(void (^)(QLPreviewReply * _Nullable reply, NSError * _Nullable error))handler
{
    NSData *pdfData = OGraphCopyPreviewPDF(request.fileURL);
    if (pdfData == nil) {
        NSError *error = [NSError errorWithDomain:NSCocoaErrorDomain code:NSFileReadCorruptFileError
                                         userInfo:@{NSLocalizedDescriptionKey: @"This GraphSketcher document has no embedded preview."}];
        handler(nil, error);
        return;
    }

    // Quick Look opens the preview window at the PDF's page size, and the embedded preview.pdf
    // page is the chart's canvas size -- typically a few hundred points, so the window came up
    // tiny. Re-render the page (it's vector, so losslessly) onto a page scaled up toward a
    // letter-PDF-like footprint, and the window, and the Finder preview pane, open large.
    NSData *previewData = pdfData;
    CGSize contentSize = CGSizeMake(800, 600); // fallback if the page box can't be read

    CGDataProviderRef provider = CGDataProviderCreateWithCFData((__bridge CFDataRef)pdfData);
    CGPDFDocumentRef document = provider ? CGPDFDocumentCreateWithProvider(provider) : NULL;
    CGPDFPageRef page = document ? CGPDFDocumentGetPage(document, 1) : NULL;
    if (page != NULL) {
        CGRect box = CGPDFPageGetBoxRect(page, kCGPDFCropBox);
        if (CGRectIsEmpty(box)) box = CGPDFPageGetBoxRect(page, kCGPDFMediaBox);
        if (!CGRectIsEmpty(box)) {
            contentSize = box.size;

            CGFloat const targetMaxDimension = 1200;
            CGFloat scale = targetMaxDimension / MAX(contentSize.width, contentSize.height);
            scale = MIN(MAX(scale, 1), 6); // never shrink large canvases; don't blow up tiny ones absurdly
            if (scale > 1) {
                CGRect scaledBox = CGRectMake(0, 0, ceil(contentSize.width * scale), ceil(contentSize.height * scale));
                NSMutableData *scaledData = [NSMutableData data];
                CGDataConsumerRef consumer = CGDataConsumerCreateWithCFData((__bridge CFMutableDataRef)scaledData);
                CGContextRef pdfContext = consumer ? CGPDFContextCreate(consumer, &scaledBox, NULL) : NULL;
                if (pdfContext != NULL) {
                    CGPDFContextBeginPage(pdfContext, NULL);
                    CGContextScaleCTM(pdfContext, scale, scale);
                    // Maps the page's crop box to the origin, handling any /Rotate and box offset.
                    CGContextConcatCTM(pdfContext, CGPDFPageGetDrawingTransform(page, kCGPDFCropBox, CGRectMake(0, 0, contentSize.width, contentSize.height), 0, true));
                    CGContextDrawPDFPage(pdfContext, page);
                    CGPDFContextEndPage(pdfContext);
                    CGPDFContextClose(pdfContext);
                    CGContextRelease(pdfContext);
                    if (scaledData.length > 0) {
                        previewData = scaledData;
                        contentSize = scaledBox.size;
                    }
                }
                if (consumer) CGDataConsumerRelease(consumer);
            }
        }
    }
    if (document) CGPDFDocumentRelease(document);
    if (provider) CGDataProviderRelease(provider);

    // Hand Quick Look a real PDFDocument so it uses the system's native PDF previewer. (A
    // data-based preview is shown at a small fixed size regardless of the content size we
    // report.)
    QLPreviewReply *reply = [[QLPreviewReply alloc] initForPDFWithPageSize:contentSize
                                                    documentCreationBlock:^PDFDocument * _Nullable(QLPreviewReply * _Nonnull replyToUpdate, NSError *__autoreleasing _Nullable * _Nullable error) {
        PDFDocument *pdfDocument = [[PDFDocument alloc] initWithData:previewData];
        if (pdfDocument == nil && error != NULL) {
            *error = [NSError errorWithDomain:NSCocoaErrorDomain code:NSFileReadCorruptFileError
                                     userInfo:@{NSLocalizedDescriptionKey: @"Could not read the embedded chart preview."}];
        }
        return pdfDocument;
    }];
    handler(reply, nil);
}

@end
