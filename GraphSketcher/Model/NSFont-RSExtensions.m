// Copyright 2003-2013 Omni Development, Inc.  All rights reserved.
//
// This software may only be used and reproduced according to the
// terms in the file OmniSourceLicense.html, which should be
// distributed with this project and can also be found at
// <http://www.omnigroup.com/developer/sourcecode/sourcelicense/>.

#import "NSFont-RSExtensions.h"

RCS_ID("$Header$");

#if !defined(TARGET_OS_IPHONE) || !TARGET_OS_IPHONE

@implementation NSFont (RSExtensions)

// -fontWithSize: removed: modern NSFont provides it natively with the same descriptor-preserving
// behavior, and a category override of a framework method is undefined (and warns under clang 21).

- (CGFloat)lineHeight;
{
    static NSLayoutManager *layoutManager = nil;
    static dispatch_once_t onceToken = 0;
    dispatch_once(&onceToken, ^{
        layoutManager = [[NSLayoutManager alloc] init];
    });
    
    return [layoutManager defaultLineHeightForFont:self];
}

@end

#endif
