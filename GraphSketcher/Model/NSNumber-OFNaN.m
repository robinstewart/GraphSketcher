//
//  Omni-Framework-Extensions.m
//  GraphSketcherModel
//
//  Created by Robin Stewart on 10/1/18.
//

#import "NSNumber-OFNaN.h"

// Copied from OmniFoundation/NSNumber-OFExtensions

@implementation OFNaN
+ (OFNaN *)sharedNaN;
{
    static OFNaN *sharedNaN = nil;
    if (!sharedNaN) {
        sharedNaN = [[OFNaN alloc] init];
    }
    return sharedNaN;
}
- (const char *)objCType;
{
    return @encode(float);
}
- (CGFloat)cgFloatValue;
{
    return NAN;
}
- (float)floatValue;
{
    return NAN;
}
- (double)doubleValue;
{
    return NAN;
}
- (id)retain;
{
    return self;
}
- (id)autorelease;
{
    return self;
}
- (oneway void)release;
{
}
- (id)copyWithZone:(NSZone *)zone;
{
    return self;
}
- (NSString *)description;
{
    return @"NaN";
}
- (NSString *)stringValue
{
    return @"NaN";
}
@end
