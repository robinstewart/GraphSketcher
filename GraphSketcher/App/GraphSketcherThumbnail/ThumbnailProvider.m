//
//  ThumbnailProvider.m
//  GraphSketcherThumbnail
//
//  Provides Finder thumbnails for GraphSketcher (.ograph) documents by rendering the vector chart
//  preview (preview.pdf) embedded in each document. See OGraphPreviewExtraction.h.
//

#import "ThumbnailProvider.h"
#import <CoreGraphics/CoreGraphics.h>
#import "../OGraphPreviewExtraction.h"

@implementation ThumbnailProvider

- (void)provideThumbnailForFileRequest:(QLFileThumbnailRequest *)request completionHandler:(void (^)(QLThumbnailReply * _Nullable, NSError * _Nullable))handler {

    NSData *pdfData = OGraphCopyPreviewPDF(request.fileURL);
    if (pdfData == nil) {
        // No embedded preview (raw-XML / autosaved / older file): let Quick Look use the default icon.
        handler(nil, nil);
        return;
    }

    // Measure the page so we can size the thumbnail to the chart's aspect ratio.
    CGSize pageSize = CGSizeZero;
    {
        CGDataProviderRef provider = CGDataProviderCreateWithCFData((__bridge CFDataRef)pdfData);
        CGPDFDocumentRef document = provider ? CGPDFDocumentCreateWithProvider(provider) : NULL;
        CGPDFPageRef page = document ? CGPDFDocumentGetPage(document, 1) : NULL;
        if (page != NULL) {
            CGRect box = CGPDFPageGetBoxRect(page, kCGPDFCropBox);
            if (CGRectIsEmpty(box)) box = CGPDFPageGetBoxRect(page, kCGPDFMediaBox);
            pageSize = box.size;
        }
        if (document) CGPDFDocumentRelease(document);
        if (provider) CGDataProviderRelease(provider);
    }
    if (pageSize.width < 1 || pageSize.height < 1) {
        handler(nil, nil);
        return;
    }

    // Aspect-fit the page into the requested maximum size (in points).
    CGSize maxSize = request.maximumSize;
    CGFloat fitScale = MIN(maxSize.width / pageSize.width, maxSize.height / pageSize.height);
    if (fitScale <= 0 || !isfinite(fitScale)) fitScale = 1.0;
    CGSize thumbSize = CGSizeMake(floor(pageSize.width * fitScale), floor(pageSize.height * fitScale));
    if (thumbSize.width < 1) thumbSize.width = 1;
    if (thumbSize.height < 1) thumbSize.height = 1;

    // Quick Look's drawing-block context is contextSize * request.scale PIXELS, with an unscaled
    // (pixel) coordinate system -- so we draw into the full pixel extent. Drawing into just
    // `thumbSize` would leave the chart in the bottom-left corner on Retina/high-DPI requests.
    CGFloat deviceScale = (request.scale > 0) ? request.scale : 1.0;
    CGRect drawRect = CGRectMake(0, 0, thumbSize.width * deviceScale, thumbSize.height * deviceScale);

    // The drawing block may run after this method returns, so it re-creates the PDF from the
    // captured data (rather than capturing CG objects whose lifetime we'd have to manage).
    QLThumbnailReply *reply = [QLThumbnailReply replyWithContextSize:thumbSize drawingBlock:^BOOL(CGContextRef _Nonnull context) {
        CGDataProviderRef provider = CGDataProviderCreateWithCFData((__bridge CFDataRef)pdfData);
        CGPDFDocumentRef document = provider ? CGPDFDocumentCreateWithProvider(provider) : NULL;
        CGPDFPageRef page = document ? CGPDFDocumentGetPage(document, 1) : NULL;
        BOOL drewSomething = NO;
        if (page != NULL) {
            // White backing so transparent regions of the chart read correctly.
            CGContextSetRGBFillColor(context, 1.0, 1.0, 1.0, 1.0);
            CGContextFillRect(context, drawRect);
            // Scale the PDF page to fill the full pixel extent of the thumbnail context.
            CGAffineTransform t = CGPDFPageGetDrawingTransform(page, kCGPDFCropBox, drawRect, 0, true);
            CGContextConcatCTM(context, t);
            CGContextDrawPDFPage(context, page);
            drewSomething = YES;
        }
        if (document) CGPDFDocumentRelease(document);
        if (provider) CGDataProviderRelease(provider);
        return drewSomething;
    }];
    handler(reply, nil);
}

@end
