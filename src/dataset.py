import os, time, datetime, csv, sys, json
import cfg
from Bio import SeqIO

class Dataset:
    '''
    Defines 'Dataset' class, containing procedures for uploading documents from un-cleaned FASTA files
    and turning them into rich JSONs that can be:
        - Uploaded to the fauna database
        - imported directly by augur (does not take JSONs at this time, instead needs FASTAs)

    Each instance of a Dataset contains:
        1. metadata: list of high level information that governs how the data contained in the Dataset
        are treated by Dataset cleaning functions (TODO: Make these in external scripts as a library of
        functions that can be imported by the Dataset), as well as the exact location in the fauna
        database where the dataset should be stored (TODO: specify in a markdown file somewhere exactly
        what the fauna db should look like).

        ex. [FIGURE OUT WHAT THIS WILL LOOK LIKE]

        2. dataset: A list of dictionaries, each one identical in architecture representing 'documents'
        that are contained within the Dataset. These dictionaries represent both lower-level metadata,
        as well as the key information (sequence, titer, etc) that is being stored/run in augur.

        ex. [ {date: 2012-06-11, location: Idaho, sequence: GATTACA}, {date: 2016-06-16, location: Oregon, sequence: CAGGGCCTCCA}, {date: 1985-02-22, location: Brazil, sequence: BANANA} ]
    '''
    def __init__(self, datatype, virus, **kwargs):
        # Wrappers for data, described in class description
        self.metadata = {'datatype': datatype, 'virus': virus}
        self.dataset = []
        if 'subtype' in kwargs.keys():
            self.metadata['subtype'] = kwargs['subtype']

        self.read_files(datatype, **kwargs)

        for i in range(len(dataset)):
            self.clean(dataset[i], i)
        self.remove_bad_docs()

    def read_files(self, datatype, infiles, ftype, **kwargs):
        '''
        Look at all infiles, and determine what file type they are. Based in that determination,
        import each file individually.
        '''
        if datatype == 'sequence':
            fasta_suffixes = ['fasta', 'fa', 'f']
            # Set fields that will be used to key into fauna table, these should be unique for every document
            self.index_fields = ['accession','locus']
            if ftype.lower() in fasta_suffixes:
                for infile in infiles:
                    self.read_fasta(infile, datatype=datatype, **kwargs)
            else:
                pass

    def read_fasta(self, infile, source, path, datatype, **kwargs):
        '''
        Take a fasta file and a list of information contained in its headers
        and build a dataset object from it.
        '''
        print 'Reading in %s FASTA from %s%s.' % (source,path,infile)
        self.fasta_headers = cfg.fasta_headers[source.lower()]
        self.seed(datatype)

        out = []

        # Read the fasta
        with open(path + infile, "rU") as f:

            for record in SeqIO.parse(f, "fasta"):
                data = {}
                head = record.description.replace(" ","").split('|')
                for i in range(len(self.fasta_headers)):
                    data[self.fasta_headers[i]] = head[i]
                    data['sequence'] = str(record.seq)

                index = []
                for ind in self.index_fields:
                    try:
                        index.append(data[ind])
                        out.append({":".join(index): data})
                    except:
                        pass

        # Merge the formatted dictionaries to self.dataset()
        print "Merging input FASTA to %s documents." % (len(out))
        for doc in out:
            try:
                assert type(doc) == dict
            except:
                print 'WARNING: Cannot merge doc of type %s: %s' % (type(doc), (str(doc)[:75] + '..') if len(str(doc)) > 75 else str(doc))
                pass
            self.merge(doc)
        print "Successfully merged %s documents. Done reading %s." % (len(self.dataset)-1, infile)


    def read_xml(self):
        '''
        Read an xml file to a metadata dataset
        '''
        return

    def merge(self, data):
        '''
        Make sure all new entries to the dataset have matching keys
        '''
        match = True
        indices = data.keys()
        for doc in indices:
            for key in data[doc]:
                if key not in self.dataset[0]['seed'].keys():
                    print('Error adding ' + key + ' to dataset, keys don\'t match.')
                    match = False

        if match:
            self.dataset.append(data)

    def clean(self, doc, key):
        '''
        Take a document and return a canonicalized version of that document
        # TODO: Incorporate all the necessary cleaning functions
        '''
        import cfg as c
        # Track which
        self.bad_docs = []

        # Remove seed
        # More efficient on large datasets than self.dataset = self.dataset[1:]
        t = self.dataset[0]
        self.dataset[0] = self.dataset[-1]
        self.dataset[-1] = t
        self.dataset = self.dataset[:-1]

        # Remove docs with bad keys or that are not of type dict
        try:
            assert type(doc) == dict
            try:
                assert len(doc.keys()) == 1
            except:
                print 'Documents should have eactly 1 key, this has %s: %s' % (len(doc.keys()), doc)
                return
        except:
            print 'Documents must be of type dict, this one is of type %s:\n%s' % (type(doc), doc)
            return

        # Use functions specified by cfg.py. Fxn defs in cleaning_functions.py
        if self.metadata['datatype'] == 'sequence':
            fxns = c.sequence_clean
        elif self.metadata['datatype'] == 'titer':
            fxns = c.titer_clean

        for fxn in fxns:
            fxn(doc[key], key, self.bad_docs)

    def remove_bad_docs(self):

        # Not working because of key errors, they should be ints
        if self.bad_docs != []:
            print self.bad_docs
            self.bad_docs = self.bad_docs.sort().reverse()
            for key in self.bad_docs:
                t = self.dataset[key]
                self.dataset[key] = self.dataset[-1]
                self.dataset[-1] = t
                self.dataset.pop()


    def write(self, out_file, out_type='json'):
        '''
        Write self.dataset to an output file, default type is json
        '''
        print 'Writing dataset to %s' % (out_file)

        out = {}
        for key in self.metadata.keys():
            out[key] = self.metadata[key]
        out['data'] = self.dataset

        if out_type == 'json':
            with open(out_file, 'w+') as f:
                json.dump(out, f, indent=1)

    def seed(self, datatype):
        '''
        Make an empty entry in dataset that has all the necessary keys, acts as a merge filter
        '''
        if datatype == 'sequence':
            seed = {'seed' : { header : None for header in self.fasta_headers }}
            seed['seed']['sequence'] = None
            self.dataset.append(seed)
        else:
            pass
