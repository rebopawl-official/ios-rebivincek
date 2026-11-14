// vince-uicache: register the system apps in /Applications with LaunchServices.
//
// The root image is built on Linux, so nobody ever ran installd's system-app scan and the LaunchServices
// database knows only a handful of apps (Settings, App Store, Safari, ...), no app extensions (PosterBoard
// finds no wallpaper provider). This does what uicache does on a jailbroken iOS, in two steps:
//   1. -[LSApplicationWorkspace _LSPrivateRebuildApplicationDatabasesForSystemApps:internal:user:]
//   2. for every /Applications/*.app that is still missing: registerApplicationDictionary: (Info.plist +
//      ApplicationType=System + Path)
// Every line starts with "uicache:" and goes to stdout (/dev/console when run from launchd).
// Usage: vince-uicache [--force]     (without --force it runs once; the marker is /var/mobile/.vince-uicache)
#import <Foundation/Foundation.h>
#import <objc/message.h>
#import <dlfcn.h>
#import <notify.h>
#import <sys/stat.h>

#define MARKER "/var/mobile/.vince-uicache"

static NSUInteger installedCount(id ws) {
	if ([ws respondsToSelector:@selector(allInstalledApplications)])
		return [[ws performSelector:@selector(allInstalledApplications)] count];
	return 0;
}

static BOOL has(id ws, NSString *bid) {
	if (![ws respondsToSelector:@selector(applicationIsInstalled:)]) return NO;
	return ((BOOL (*)(id, SEL, id))objc_msgSend)(ws, @selector(applicationIsInstalled:), bid);
}

int main(int argc, char **argv) {
	@autoreleasepool {
		BOOL force = argc > 1 && !strcmp(argv[1], "--force");
		struct stat st;
		if (!force && !stat(MARKER, &st)) { printf("uicache: already done (%s), use --force\n", MARKER); return 0; }

		dlopen("/System/Library/Frameworks/MobileCoreServices.framework/MobileCoreServices", RTLD_NOW);
		dlopen("/System/Library/Frameworks/CoreServices.framework/CoreServices", RTLD_NOW);
		Class cls = objc_getClass("LSApplicationWorkspace");
		id ws = cls ? [cls performSelector:@selector(defaultWorkspace)] : nil;
		if (!ws) { printf("uicache: no LSApplicationWorkspace\n"); return 1; }

		NSArray *dirs = [[NSFileManager defaultManager] contentsOfDirectoryAtPath:@"/Applications" error:nil];
		NSMutableArray *apps = [NSMutableArray array];
		for (NSString *d in dirs) if ([d hasSuffix:@".app"]) [apps addObject:d];
		printf("uicache: %lu apps in /Applications, %lu known to LaunchServices\n",
		       (unsigned long)apps.count, (unsigned long)installedCount(ws));

		SEL rebuild = NSSelectorFromString(@"_LSPrivateRebuildApplicationDatabasesForSystemApps:internal:user:");
		if ([ws respondsToSelector:rebuild]) {
			BOOL r = ((BOOL (*)(id, SEL, BOOL, BOOL, BOOL))objc_msgSend)(ws, rebuild, YES, YES, NO);
			printf("uicache: rebuild(system) -> %d, now %lu known\n", r, (unsigned long)installedCount(ws));
		} else {
			printf("uicache: rebuild selector missing\n");
		}

		SEL regdict = NSSelectorFromString(@"registerApplicationDictionary:");
		SEL regurl = NSSelectorFromString(@"registerApplication:");
		unsigned added = 0, failed = 0;
		for (NSString *d in apps) {
			NSString *path = [@"/Applications" stringByAppendingPathComponent:d];
			NSMutableDictionary *info = [NSMutableDictionary dictionaryWithContentsOfFile:[path stringByAppendingPathComponent:@"Info.plist"]];
			NSString *bid = info[@"CFBundleIdentifier"];
			if (!bid) { printf("uicache: %s: no Info.plist\n", d.UTF8String); failed++; continue; }
			if (has(ws, bid)) continue;
			info[@"ApplicationType"] = @"System";
			info[@"Path"] = path;
			BOOL ok = NO;
			if ([ws respondsToSelector:regdict])
				ok = ((BOOL (*)(id, SEL, id))objc_msgSend)(ws, regdict, info);
			if (!ok && [ws respondsToSelector:regurl])
				ok = ((BOOL (*)(id, SEL, id))objc_msgSend)(ws, regurl, [NSURL fileURLWithPath:path]);
			printf("uicache: %s (%s) -> %d\n", d.UTF8String, bid.UTF8String, ok);
			ok ? added++ : failed++;
		}
		notify_post("com.apple.mobile.application_installed");
		printf("uicache: added %u, failed %u, %lu known now\n", added, failed, (unsigned long)installedCount(ws));
		fflush(stdout);
		FILE *f = fopen(MARKER, "w"); if (f) fclose(f);
		return failed ? 2 : 0;
	}
}
