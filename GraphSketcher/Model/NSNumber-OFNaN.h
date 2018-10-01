//
//  Omni-Framework-Extensions.h
//  GraphSketcherModel
//
//  Created by Robin Stewart on 10/1/18.
//

#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

// Copied from OmniFoundation/NSNumber-OFExtensions

// This class exists due to Radar #3478597 where NaN numbers aren't correctly compared.  This returns something that is truly 'Not a Number' and thus the CF comparison works out better.  Of course, it really isn't a NSNumber, so care must be taken that it isn't used as one.
@interface OFNaN : NSObject
+ (OFNaN *)sharedNaN;
@end

NS_ASSUME_NONNULL_END
