#!/usr/bin/env perl
use strict;
use warnings;

use List::MoreUtils qw(first_index first_value);
# use Archive::Zip qw( :ERROR_CODES :CONSTANTS );
use Archive::Zip::CONSTANTS;

# /^(?<dir>[\-ld])(?<permission>([\-r][\-w][\-xs]){3})\s+(?<filecode>\d+)\s+(?<owner>\w+)\s+(?<group>\w+)\s+(?<size>\d+)\s+(?<timestamp>((?<month>\w{3})\s+(?<day>\d{1,2})\s+(?<hour>\d{1,2}):(?<minute>\d{2}))|((?<month2>\w{3})\s+(?<day2>\d{1,2})\s+(?<year>\d{4})))\s+(?<name>.+)$/;

my $a = 'downloads/pic.jpg';
my @arr = qw(downloads pic.jpg);
$a =~ /^(?<dir>[^\/]*)\/(?<filename>[^\/]*)$/;

print CONSTANTS::AZ_OK;

# if($+{dir} eq 'downloads'){
#  print 2;
# }


# print 'ld-' =~ /[\-d]/;
