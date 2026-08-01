//
//  OGraphPreviewExtraction.h
//  Shared by the GraphSketcher Quick Look thumbnail + preview extensions.
//
//  A .ograph document is a flat ZIP archive containing "contents.xml" and (for any document saved
//  normally, with the IncludeQuicklookPreview preference on) a root-level "preview.pdf" -- a vector
//  render of the chart. These helpers pull that preview.pdf out of the zip using ONLY Foundation
//  (NSData's built-in DEFLATE), so the sandboxed Quick Look extensions need no extra frameworks or
//  libraries and stay self-contained. Returns nil for raw-XML / autosaved / preview-less files; the
//  caller should then fall back to the system's default document icon.
//
//  Header-only (static functions) on purpose: the two extensions are separate file-system-
//  synchronized Xcode targets, so a normal shared .m would have to be added to both target groups.
//  Sharing via #import "../OGraphPreviewExtraction.h" avoids any project-file changes.
//

#import <Foundation/Foundation.h>
#import <string.h>

static inline uint16_t OGraphRead16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static inline uint32_t OGraphRead32(const uint8_t *p) { return (uint32_t)(p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24)); }

// Extract the bytes of the entry named `entryName` from the ZIP archive in `data` (supports the two
// methods these documents use: stored and DEFLATE). Returns nil if `data` is not a zip (e.g. a
// raw-XML autosave) or the entry is absent.
static NSData *OGraphCopyZipEntry(NSData *data, NSString *entryName) {
    const uint8_t *b = (const uint8_t *)data.bytes;
    NSUInteger n = data.length;
    // Must begin with a local file header ("PK\3\4"); raw-XML saves won't.
    if (n < 22 || !(b[0] == 'P' && b[1] == 'K' && b[2] == 3 && b[3] == 4))
        return nil;

    // Locate the End Of Central Directory record by scanning backwards for its signature "PK\5\6".
    NSInteger eocd = -1;
    for (NSInteger i = (NSInteger)n - 22; i >= 0; i--) {
        if (b[i] == 'P' && b[i + 1] == 'K' && b[i + 2] == 5 && b[i + 3] == 6) { eocd = i; break; }
    }
    if (eocd < 0)
        return nil;

    uint32_t centralDirOffset = OGraphRead32(b + eocd + 16);
    uint16_t entryCount = OGraphRead16(b + eocd + 10);
    NSData *wantData = [entryName dataUsingEncoding:NSUTF8StringEncoding];

    NSUInteger p = centralDirOffset;
    for (uint16_t e = 0; e < entryCount; e++) {
        if (p + 46 > n || !(b[p] == 'P' && b[p + 1] == 'K' && b[p + 2] == 1 && b[p + 3] == 2))
            return nil;
        uint16_t method = OGraphRead16(b + p + 10);
        uint32_t compressedSize = OGraphRead32(b + p + 20);
        uint32_t uncompressedSize = OGraphRead32(b + p + 24);
        uint16_t nameLen = OGraphRead16(b + p + 28);
        uint16_t extraLen = OGraphRead16(b + p + 30);
        uint16_t commentLen = OGraphRead16(b + p + 32);
        uint32_t localOffset = OGraphRead32(b + p + 42);

        if (nameLen == wantData.length && memcmp(b + p + 46, wantData.bytes, nameLen) == 0) {
            if (localOffset + 30 > n ||
                !(b[localOffset] == 'P' && b[localOffset + 1] == 'K' && b[localOffset + 2] == 3 && b[localOffset + 3] == 4))
                return nil;
            // The local header's own name/extra lengths determine where the entry data begins.
            NSUInteger dataOffset = localOffset + 30 + OGraphRead16(b + localOffset + 26) + OGraphRead16(b + localOffset + 28);
            if (dataOffset + compressedSize > n)
                return nil;

            NSData *rawEntry = [NSData dataWithBytes:b + dataOffset length:compressedSize];
            if (method == 0)  // stored
                return rawEntry;
            if (method == 8) {  // DEFLATE -- NSData's Zlib algorithm is the raw RFC-1951 DEFLATE stream
                NSData *inflated = [rawEntry decompressedDataUsingAlgorithm:NSDataCompressionAlgorithmZlib error:NULL];
                return (inflated.length == uncompressedSize) ? inflated : nil;
            }
            return nil;  // unsupported compression method
        }
        p += 46 + nameLen + extraLen + commentLen;
    }
    return nil;
}

// Returns the embedded vector chart preview (preview.pdf) for the .ograph at `url`, or nil if the
// document has no embedded preview (raw-XML / autosaved / older files).
static NSData *OGraphCopyPreviewPDF(NSURL *url) {
    NSData *file = [NSData dataWithContentsOfURL:url options:NSDataReadingMappedIfSafe error:NULL];
    if (file == nil)
        return nil;
    NSData *pdf = OGraphCopyZipEntry(file, @"preview.pdf");
    if (pdf.length > 4 && memcmp(pdf.bytes, "%PDF", 4) == 0)
        return pdf;
    return nil;
}
