"""
Module implementing simple Peer Tube GUI for a simple p2p network.
 # python -m peer2peertube.main.py 8888 5 127.0.0.1:8889 alias
"""
from tkinter import *

from .fileutils import *


class Gui(Frame):
    def __init__(self, firstpeer, hops=2, maxpeers=5, serverport=5678, alias='tmp', master=None):
        Frame.__init__(self, master)
        self.grid()
        self.createWidgets()
        self.master.title("%s: %d" % (alias, serverport))
        self.peer = FilerPeer(maxpeers, serverport, alias)
        self.peer.load_all_peer_saved()
        self.peer.reestablish_connections()

        self.bind("<Destroy>", self.__onDestroy)

        host, port = firstpeer.split(':')
        self.peer.buildpeers(host, int(port), hops=hops)
        self.updatePeerList()

        t = threading.Thread(target=self.peer.mainloop, args=[])
        t.start()

        self.peer.startstabilizer(self.peer.checklivepeers, 3)
        self.after(3000, self.onTimer)

    def onTimer(self):
        self.onRefresh()
        self.after(3000, self.onTimer)

    def __onDestroy(self, event):
        self.peer.dump_peer()
        self.peer.shutdown = True

    def updatePeerList(self):
        if self.peerList.size() > 0:
            self.peerList.delete(0, self.peerList.size() - 1)
        for p in self.peer.getpeerids():
            self.peerList.insert(END, p)

    def updateFileList(self):
        if self.fileList.size() > 0:
            self.fileList.delete(0, self.fileList.size() - 1)
        for f in self.peer.files:
            p = self.peer.files[f]
            if not p:
                p = '(local)'
            self.fileList.insert(END, "%s:%s" % (f, p))

    def createWidgets(self):
        """
        Set up the frame widgets
        """
        fileFrame = Frame(self)
        peerFrame = Frame(self)

        rebuildFrame = Frame(self)
        searchFrame = Frame(self)
        addfileFrame = Frame(self)
        pbFrame = Frame(self)

        fileFrame.grid(row=0, column=0, sticky=N + S)
        peerFrame.grid(row=0, column=1, sticky=N + S)
        pbFrame.grid(row=2, column=1)
        addfileFrame.grid(row=3)
        searchFrame.grid(row=4)
        rebuildFrame.grid(row=3, column=1)

        Label(fileFrame, text='Available Files').grid()
        Label(peerFrame, text='Peer List').grid()

        fileListFrame = Frame(fileFrame)
        fileListFrame.grid(row=1, column=0)
        fileScroll = Scrollbar(fileListFrame, orient=VERTICAL)
        fileScroll.grid(row=0, column=1, sticky=N + S)

        self.fileList = Listbox(fileListFrame, height=5,
                                yscrollcommand=fileScroll.set)
        self.fileList.grid(row=0, column=0, sticky=N + S)
        fileScroll["command"] = self.fileList.yview

        self.fetchButton = Button(fileFrame, text='Fetch',
                                  command=self.onFetch)
        self.fetchButton.grid()

        self.addfileEntry = Entry(addfileFrame, width=25)
        self.addfileButton = Button(addfileFrame, text='Add',
                                    command=self.onAdd)
        self.addfileEntry.grid(row=0, column=0)
        self.addfileButton.grid(row=0, column=1)

        self.searchEntry = Entry(searchFrame, width=25)
        self.searchButton = Button(searchFrame, text='Search',
                                   command=self.onSearch)
        self.searchEntry.grid(row=0, column=0)
        self.searchButton.grid(row=0, column=1)

        peerListFrame = Frame(peerFrame)
        peerListFrame.grid(row=1, column=0)
        peerScroll = Scrollbar(peerListFrame, orient=VERTICAL)
        peerScroll.grid(row=0, column=1, sticky=N + S)

        self.peerList = Listbox(peerListFrame, height=5,
                                yscrollcommand=peerScroll.set)
        self.peerList.grid(row=0, column=0, sticky=N + S)
        peerScroll["command"] = self.peerList.yview

        self.removeButton = Button(pbFrame, text='Remove',
                                   command=self.onRemove)
        self.refreshButton = Button(pbFrame, text='Refresh',
                                    command=self.onRefresh)

        self.rebuildEntry = Entry(rebuildFrame, width=25)
        self.rebuildButton = Button(rebuildFrame, text='Rebuild',
                                    command=self.onRebuild)
        self.removeButton.grid(row=0, column=0)
        self.refreshButton.grid(row=0, column=1)
        self.rebuildEntry.grid(row=0, column=0)
        self.rebuildButton.grid(row=0, column=1)

    """callbacks for various actions performed on the GUI
    """

    def onAdd(self):
        file = self.addfileEntry.get()
        if file.lstrip().rstrip():
            filename = file.lstrip().rstrip()
            self.peer.addlocalfile(filename)
        self.addfileEntry.delete(0, len(file))
        self.updateFileList()

    def onSearch(self):
        key = self.searchEntry.get()
        self.searchEntry.delete(0, len(key))

        for p in self.peer.getpeerids():
            self.peer.sendtopeer(p, QUERY, "%s %s 4" % (self.peer.myid, key))

    def onFetch(self):
        sels = self.fileList.curselection()
        if len(sels) == 1:
            sel = self.fileList.get(sels[0]).split(':')
            if len(sel) > 2:  # fname:host:port
                fname, host, port = sel
                resp = self.peer.connectandsend(host, port, FILEGET, fname)

    def onRemove(self):
        sels = self.peerList.curselection()
        if len(sels) == 1:
            peerid = self.peerList.get(sels[0])
            self.peer.sendtopeer(peerid, PEERQUIT, self.peer.myid)
            self.peer.removepeer(peerid)

    def onRefresh(self):
        self.updatePeerList()
        self.updateFileList()

    def onRebuild(self):
        if not self.peer.maxpeersreached():
            peerid = self.rebuildEntry.get()
            self.rebuildEntry.delete(0, len(peerid))
            peerid = peerid.lstrip().rstrip()
            try:
                host, port = peerid.split(':')
                # print "doing rebuild", peerid, host, port
                self.peer.buildpeers(host, port, hops=3)
            except:
                if self.peer.debug:
                    traceback.print_exc()


def main():
    if len(sys.argv) < 4:
        print("Syntax: %s server-port max-peers peer-ip:port" % sys.argv[0])
        sys.exit(-1)

    serverport = int(sys.argv[1])
    maxpeers = sys.argv[2]
    peerid = sys.argv[3]
    alias = sys.argv[4]
    app = Gui(firstpeer=peerid, maxpeers=maxpeers, serverport=serverport, alias=alias)
    app.mainloop()


# setup and run app
if __name__ == '__main__':
    main()
