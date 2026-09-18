import shutil

from gittrail_core.pipeline import create_track, display_track_in_txt, init_local, init_remote


def main():
    path = ""
    is_remote = False
    while not path:
        print("What kind of repository do you want to analyze?\n\t[1] local\n\t[2] remote")
        choice = input().strip()
        if choice == "1":
            path = init_local()
        elif choice == "2":
            print("Please paste the remote Git URL (e.g., https://github.com/...):")
            url = input().strip()
            path = init_remote(url)
            is_remote = True
        else:
            print("ivalid input")

    # TODO: as soon as we implement an update-function:
    #print("What do you want to do?\n\t[1] new track\n\t[2] update track")
    #
    #
    create_track(path)
    # 
    # 
    # 
    if is_remote:
        shutil.rmtree(path, ignore_errors=True)

    display_track_in_txt()



    

    

if __name__ == "__main__":
    main()