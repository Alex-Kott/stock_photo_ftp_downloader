#!/usr/bin/env perl
use strict;
use warnings;


 /^(?<dir>[\-ld])(?<permission>([\-r][\-w][\-xs]){3})\s+(?<filecode>\d+)\s+(?<owner>\w+)\s+(?<group>\w+)\s+(?<size>\d+)\s+(?<timestamp>((?<month>\w{3})\s+(?<day>\d{1,2})\s+(?<hour>\d{1,2}):(?<minute>\d{2}))|((?<month2>\w{3})\s+(?<day2>\d{1,2})\s+(?<year>\d{4})))\s+(?<name>.+)$/

print 'ld-' =~ /[\-d]/;
