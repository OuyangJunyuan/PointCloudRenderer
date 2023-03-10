def init_mitsuba(cfgs, args):
    import mitsuba
    print(mitsuba.variants())
    print(f'set mitsuba variant as {cfgs.variant}')
    mitsuba.set_variant(cfgs.variant)
    if not cfgs.verbose:
        mitsuba.Thread.thread().logger().set_log_level(mitsuba.LogLevel.Warn)
