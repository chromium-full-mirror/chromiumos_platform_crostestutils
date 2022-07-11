# Launchbugs Redirect

Launchbugs.html is a helper that opens filtered launchbugs based on Milestones, Test Engineers,
Status, and component IIRC

## Usage
Navigate to [go/launchbugs?]
Filter by Milestone: [go/launchbugs?m=105]
Filter by Test Engineers: [go/launchbugs?te=dhaddock]
Filter by Status: [go/launchbugs?m=105&s=Fixed]
Filter by Component IIRC: [go/launchbugs?c=UI>Shell>StatusArea]
Filter by Team: [go/launchbugs?team=coreX]

## Filtering by Team
Team is not an existing Filter in LaunchBugs. The functionality was added to shorten the Tests Engineers required if we want to add all the TEs from CoreX.
Ex: `go/launchbugs?m=100&team=coreX` will search for all the Launch Bugs in Milestone 100 where the TEs are dhaddock,kyleshima,hyungtaekim, or awendy

## Testing
After modifying the script, please make sure that the old functionalities are still working, some good urls to test:
- [go/launchbugs?]
- [go/launchbugs?te=new]
- [go/launchbugs?m=105]
- [go/launchbugs?m=105&te=dhaddock]
- [go/launchbugs?team=corex]
- [go/launchbugs?team=corex&m=105]
- [go/launchbugs?&m=101&te=dhaddock&s=Fixed]
- [go/launchbugs?team=corex&m=101&te=sdantuluri&status=Fixed&c=OS>Systems>Update]

[//]: # (Reference Links)
[go/launchbugs?]: go/launchbugs?
[go/launchbugs?te=new]: go/launchbugs?te=new
[go/launchbugs?te=dhaddock]: go/launchbugs?te=dhaddock
[go/launchbugs?m=105&s=Fixed]: go/launchbugs?m=105&s=Fixed
[go/launchbugs?c=UI>Shell>StatusArea]: go/launchbugs?c=UI>Shell>StatusArea
[go/launchbugs?m=105]: go/launchbugs?m=105
[go/launchbugs?m=105&te=dhaddock]: go/launchbugs?m=105&te=dhaddock
[go/launchbugs?team=corex]: go/launchbugs?team=corex
[go/launchbugs?team=corex&m=105]: go/launchbugs?team=corex&m=105
[go/launchbugs?&m=101&te=dhaddock&s=Fixed]: go/launchbugs?&m=101&te=dhaddock&s=Fixed
[go/launchbugs?team=corex&m=101&te=sdantuluri&status=Fixed&c=OS>Systems>Update]: go/launchbugs?team=corex&m=101&te=sdantuluri&status=Fixed&c=OS>Systems>Update
