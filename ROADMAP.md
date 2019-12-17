ListenBrainz Roadmap
====================

Updated Autumn 2019

We're currently working on a number of fronts, with several larger features
being incomplete at this time. Our short term focus should be to finish 
features, test them and then release these features before we start any more
new features:

 - User statistics - after our misfortune trying to use BigQuery for our user
   statistics, we've been working on creating our own BigData infrastructure for
   calculating user statistics. We're nearly done migrating to the new framework --
   we have some clanup and final integration to do, then the features has at least
   one graph. After we release this features we should appeal to our end users to
   both ask what graphs we should create and to ask people to help us make new graphs.

 - Follow page - We've been hacking on the follow page as our first attempt to add
   some social features into ListenBrainz. However, a buggy player and our crude
   UI is preventing users from using this feature. Monkey has made recent improvements
   to the player, so that portion of the work may very well be nearly usable now.
   We will need to revamp the UI to be a little more clear and we will need to
   add a feature to our recent listens page to follow a user from there.

Once we have a release with the above features working reasonably well, we should 
attempt to get more people to record their listens with Spotify. We could attempt to
get an article on Hacker News that appeals to users to record their listens, import
from last.fm and also tell us what their favorite graphs from last.fm were.

Recommendation features
-----------------------

Our short term goal should be to create 3 data sets that can serve as the foundation
for the beginnings of recommendation tools. Each data set should come with an example
application that outlines what can be done with each of the datasets we have:

- artist-artist relationships: This data set, which was derived from examining 
  the Various Artist albums on MusicBrainz, provides lists of two artist MBIDs
  and a relation value (parametric) between the two. This simple data set can have
  many uses, but the first and easy demonstration app should be an artist explorer,
  where the user can search for an artist and then explore related artists by clicking on
  the artists and seeing critical information from MB displayed on those pages. From
  each artist page the user should be able to jump off to MusicBrainz' artist page
  or click on related artists.

- track-track similarity: This dataset, grown out of AcousticBrainz, contains a set
  of indexes that allows the user to look up a given track and find tracks that are 
  similar to it, given up to 12 different metrics. These indexes should be considered
  the first order approximation -- the results from these indexes will likely need to be
  filtered with the low/high level data of the AcousticBrainz database in order to be useful.
  The demo app for this data set is the similar track artist page that Monkey and ruaok
  have been working on.

- user-user collaborative filtering: This dataset 

